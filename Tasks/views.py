# chat/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import StreamingHttpResponse
from rest_framework import status
from LLM import model_backend_mapping
import json
import time

class ChatCompletionView(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data
        model = data.get("model")
        messages = data.get("messages", [])
        temperature = data.get("temperature", 1.0)
        stream = data.get("stream", False)

        backend = model_backend_mapping.get(model)
        if backend is None:
            return Response({"error": "Model not found"}, status=status.HTTP_200_OK)

        if stream:
            return StreamingHttpResponse(
                self.stream_response(backend, messages, temperature),
                content_type='text/event-stream',
            )
        else:
            full_content = ""
            for chunk in backend.chat(messages):
                full_content += chunk

            response = {
                "id": "chatcmpl-non-streaming",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": full_content
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            }
            return Response(response, status=status.HTTP_200_OK)

    def stream_response(self, backend, messages, temperature):

        for chunk in backend.chat(messages):
            content = {
                "id": "chatcmpl-streaming",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "stream-model",
                "choices": [
                    {
                        "delta": {
                            "content": chunk
                        },
                        "index": 0,
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(content)}\n\n"
        # 结束标志
        yield "data: [DONE]\n\n"
