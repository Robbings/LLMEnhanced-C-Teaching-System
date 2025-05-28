from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock
import json
import time


class ChatCompletionViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('chat-completion')
        self.valid_payload = {
            "model": "mock-model",
            "messages": [{"role": "user", "content": "Hello"}],
            "temperature": 0.7
        }

    @patch('Tasks.views.model_backend_mapping')
    def test_post_non_streaming_success(self, mock_backend_mapping):
        """Test successful non-streaming chat completion"""
        # 配置模拟对象
        mock_backend = MagicMock()
        mock_backend.chat.return_value = ["Hello", " world", "!"]
        mock_backend_mapping.get.return_value = mock_backend

        # 发送请求
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )

        # 验证响应
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['choices'][0]['message']['content'], "Hello world!")
        self.assertEqual(data['object'], "chat.completion")

        # 验证调用
        mock_backend_mapping.get.assert_called_once_with("mock-model")
        mock_backend.chat.assert_called_once_with(self.valid_payload["messages"])

    @patch('Tasks.views.model_backend_mapping')
    def test_post_streaming_success(self, mock_backend_mapping):
        """Test successful streaming chat completion"""
        # 配置模拟对象
        mock_backend = MagicMock()
        mock_backend.chat.return_value = ["Hello", " world", "!"]
        mock_backend_mapping.get.return_value = mock_backend

        # 添加streaming参数
        self.valid_payload["stream"] = True

        # 发送请求
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )

        # 验证响应
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/event-stream')

        # 解析流响应
        content = response.streaming_content
        responses = [chunk.decode('utf-8') for chunk in content]

        # 验证流响应格式
        self.assertEqual(len(responses), 4)  # 3个数据块 + 1个结束标记

        for i in range(3):
            self.assertTrue(responses[i].startswith('data: '))
            chunk_data = json.loads(responses[i].replace('data: ', '').strip())
            self.assertEqual(chunk_data['object'], 'chat.completion.chunk')
            self.assertEqual(chunk_data['choices'][0]['delta']['content'],
                             ["Hello", " world", "!"][i])

        self.assertEqual(responses[3], 'data: [DONE]\n\n')

        # 验证调用
        mock_backend_mapping.get.assert_called_once_with("mock-model")
        mock_backend.chat.assert_called_once_with(self.valid_payload["messages"])

    @patch('Tasks.views.model_backend_mapping')
    def test_model_not_found(self, mock_backend_mapping):
        """Test when model is not found in backend mapping"""
        # 配置mock对象返回None表示模型未找到
        mock_backend_mapping.get.return_value = None

        # 发送请求
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )

        # 验证响应
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, {"error": "Model not found"})

        # 验证调用
        mock_backend_mapping.get.assert_called_once_with("mock-model")

    @patch('Tasks.views.model_backend_mapping')
    @patch('Tasks.views.time.time')
    def test_non_streaming_timestamp(self, mock_time, mock_backend_mapping):
        """Test timestamp in non-streaming response"""
        # 配置模拟对象
        mock_backend = MagicMock()
        mock_backend.chat.return_value = ["Test content"]
        mock_backend_mapping.get.return_value = mock_backend
        mock_time.return_value = 1234567890

        # 发送请求
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )

        # 验证时间戳
        data = response.json()
        self.assertEqual(data['created'], 1234567890)

    @patch('Tasks.views.model_backend_mapping')
    @patch('Tasks.views.time.time')
    def test_streaming_timestamp(self, mock_time, mock_backend_mapping):
        """Test timestamp in streaming response"""
        # 配置模拟对象
        mock_backend = MagicMock()
        mock_backend.chat.return_value = ["Test content"]
        mock_backend_mapping.get.return_value = mock_backend
        mock_time.return_value = 1234567890

        # 添加streaming参数
        self.valid_payload["stream"] = True

        # 发送请求
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )

        # 解析流响应
        content = response.streaming_content
        responses = [chunk.decode('utf-8') for chunk in content]

        # 验证时间戳
        chunk_data = json.loads(responses[0].replace('data: ', '').strip())
        self.assertEqual(chunk_data['created'], 1234567890)

    @patch('Tasks.views.model_backend_mapping')
    def test_default_parameters(self, mock_backend_mapping):
        """Test default parameters are applied correctly"""
        # 配置模拟对象
        mock_backend = MagicMock()
        mock_backend.chat.return_value = ["Test content"]
        mock_backend_mapping.get.return_value = mock_backend

        # 移除temperature字段检测默认值
        minimal_payload = {
            "model": "mock-model",
            "messages": [{"role": "user", "content": "Hello"}]
        }

        # 发送请求
        response = self.client.post(
            self.url,
            data=json.dumps(minimal_payload),
            content_type='application/json'
        )

        # 验证响应
        self.assertEqual(response.status_code, 200)

        # 验证backend.chat被正确调用
        mock_backend_mapping.get.assert_called_once_with("mock-model")
        mock_backend.chat.assert_called_once_with(minimal_payload["messages"])

    @patch('Tasks.views.model_backend_mapping')
    def test_empty_messages(self, mock_backend_mapping):
        """Test with empty messages list"""
        # 配置模拟对象
        mock_backend = MagicMock()
        mock_backend.chat.return_value = [""]
        mock_backend_mapping.get.return_value = mock_backend

        # 设置空消息列表
        payload_with_empty_messages = {
            "model": "mock-model",
            "messages": []
        }

        # 发送请求
        response = self.client.post(
            self.url,
            data=json.dumps(payload_with_empty_messages),
            content_type='application/json'
        )

        # 验证响应
        self.assertEqual(response.status_code, 200)

        # 验证backend.chat被正确调用
        mock_backend_mapping.get.assert_called_once_with("mock-model")
        mock_backend.chat.assert_called_once_with([])