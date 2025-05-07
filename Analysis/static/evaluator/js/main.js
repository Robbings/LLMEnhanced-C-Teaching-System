document.addEventListener('DOMContentLoaded', function() {
    // Initialize CodeMirror for code submission
    const codeTextarea = document.getElementById('id_code_text');
    if (codeTextarea) {
        const codeEditor = CodeMirror.fromTextArea(codeTextarea, {
            mode: 'python',
            theme: 'monokai',
            lineNumbers: true,
            indentUnit: 4,
            smartIndent: true,
            tabSize: 4,
            indentWithTabs: false,
            lineWrapping: true,
            extraKeys: {
                "Tab": function(cm) {
                    cm.replaceSelection("    ", "end");
                }
            }
        });
    }

    // Initialize CodeMirror for test case submission
    const testTextarea = document.getElementById('id_test_text');
    if (testTextarea) {
        const testEditor = CodeMirror.fromTextArea(testTextarea, {
            mode: 'python',
            theme: 'monokai',
            lineNumbers: true,
            indentUnit: 4,
            smartIndent: true,
            tabSize: 4,
            indentWithTabs: false,
            lineWrapping: true,
            extraKeys: {
                "Tab": function(cm) {
                    cm.replaceSelection("    ", "end");
                }
            }
        });
    }

    // Render markdown content
    const markdownContent = document.getElementById('markdown-content');
    if (markdownContent) {
        // Set up marked.js options
        marked.setOptions({
            renderer: new marked.Renderer(),
            highlight: function(code, lang) {
                const language = hljs.getLanguage(lang) ? lang : 'plaintext';
                return hljs.highlight(code, { language }).value;
            },
            langPrefix: 'hljs language-',
            pedantic: false,
            gfm: true,
            breaks: false,
            sanitize: false,
            smartypants: false,
            xhtml: false
        });

        // Render the markdown
        markdownContent.innerHTML = marked.parse(markdownContent.textContent);
    }

    // File upload handling
    const codeFileInput = document.getElementById('id_code_file');
    if (codeFileInput) {
        codeFileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                // Disable the code textarea when a file is selected
                if (codeEditor) {
                    codeEditor.setOption('readOnly', true);
                }
            } else {
                // Enable the code textarea when no file is selected
                if (codeEditor) {
                    codeEditor.setOption('readOnly', false);
                }
            }
        });
    }

    const testFileInput = document.getElementById('id_test_file');
    if (testFileInput) {
        testFileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                // Disable the test textarea when a file is selected
                if (testEditor) {
                    testEditor.setOption('readOnly', true);
                }
            } else {
                // Enable the test textarea when no file is selected
                if (testEditor) {
                    testEditor.setOption('readOnly', false);
                }
            }
        });
    }
});