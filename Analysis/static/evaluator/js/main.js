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

    // Initialize CodeMirror for problem content
    const problemTextarea = document.getElementById('problem_content');
    if (problemTextarea) {
        const problemEditor = CodeMirror.fromTextArea(problemTextarea, {
            mode: 'markdown',
            theme: 'monokai',
            lineNumbers: true,
            lineWrapping: true,
            readOnly: true // Initially read-only
        });

        // Handle problem editing
        const editProblemBtn = document.getElementById('edit-problem-btn');
        const saveProblemBtn = document.getElementById('save-problem-btn');
        const problemIdInput = document.getElementById('problem_id');

        if (editProblemBtn && saveProblemBtn) {
            // Enable editing mode
            editProblemBtn.addEventListener('click', function() {
                problemEditor.setOption('readOnly', false);
                problemIdInput.readOnly = false;
                editProblemBtn.style.display = 'none';
                saveProblemBtn.style.display = 'inline-block';
            });

            // Save problem and disable editing
            saveProblemBtn.addEventListener('click', function() {
                const problemId = problemIdInput.value.trim();
                const problemContent = problemEditor.getValue();

                // Basic validation
                if (!problemId) {
                    alert('Problem ID cannot be empty');
                    return;
                }

                // Get CSRF token
                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

                // Send data to server
                fetch('/analysis/problem/save/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': csrfToken
                    },
                    body: `id=${encodeURIComponent(problemId)}&content=${encodeURIComponent(problemContent)}`
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Update problem ID in hidden inputs for code and test submissions
                        const codeIdInput = document.getElementById('code_problem_id');
                        const testIdInput = document.getElementById('test_problem_id');
                        if (codeIdInput) codeIdInput.value = problemId;
                        if (testIdInput) testIdInput.value = problemId;

                        // Update problem display
                        renderProblemMarkdown(problemContent);

                        // Disable editing
                        problemEditor.setOption('readOnly', true);
                        problemIdInput.readOnly = true;
                        saveProblemBtn.style.display = 'none';
                        editProblemBtn.style.display = 'inline-block';

                        // Show success message
                        alert('Problem saved successfully!');
                    } else {
                        alert('Error: ' + (data.message || 'Failed to save problem'));
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred while saving');
                });
            });
        }
    }

    // Render problem markdown on load
    const problemContent = document.getElementById('problem_content');
    if (problemContent) {
        renderProblemMarkdown(problemContent.value);
    }

    // Function to render problem markdown
    function renderProblemMarkdown(content) {
        const problemDisplay = document.getElementById('problem-display');
        if (problemDisplay) {
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
            problemDisplay.innerHTML = marked.parse(content);
        }
    }

    // Render evaluation report markdown
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

    // File upload handling for code submission
    const codeFileInput = document.getElementById('id_code_file');
    if (codeFileInput && codeEditor) {
        codeFileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                // Disable the code textarea when a file is selected
                codeEditor.setOption('readOnly', true);
            } else {
                // Enable the code textarea when no file is selected
                codeEditor.setOption('readOnly', false);
            }
        });
    }

    // File upload handling for test submission
    const testFileInput = document.getElementById('id_test_file');
    if (testFileInput && testEditor) {
        testFileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                // Disable the test textarea when a file is selected
                testEditor.setOption('readOnly', true);
            } else {
                // Enable the test textarea when no file is selected
                testEditor.setOption('readOnly', false);
            }
        });
    }
});