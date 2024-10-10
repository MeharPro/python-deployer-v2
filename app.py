import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
import sys
from io import StringIO
import contextlib
import threading
import queue

app = Flask(__name__)
DEPLOYMENT_DIR = 'deployments'

class IOManager:
    def __init__(self):
        self.output_queue = queue.Queue()
        self.input_queue = queue.Queue()

    def custom_input(self, prompt=""):
        self.output_queue.put(prompt)
        return self.input_queue.get()

    def custom_print(self, *args, **kwargs):
        output = StringIO()
        print(*args, file=output, **kwargs)
        self.output_queue.put(output.getvalue())

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/deploy', methods=['POST'])
def deploy():
    code = request.form['code']
    filename = request.form['filename']
    
    if not filename.endswith('.py'):
        filename += '.py'
    
    filepath = os.path.join(DEPLOYMENT_DIR, filename)
    
    # Ensure the filename is unique
    counter = 1
    while os.path.exists(filepath):
        name, ext = os.path.splitext(filename)
        filepath = os.path.join(DEPLOYMENT_DIR, f"{name}_{counter}{ext}")
        counter += 1
    
    # Save the code to the file
    with open(filepath, 'w') as f:
        f.write(code)
    
    return redirect(url_for('view_code', filename=os.path.basename(filepath)))

@app.route('/<filename>')
def view_code(filename):
    filepath = os.path.join(DEPLOYMENT_DIR, filename)
    if not os.path.exists(filepath):
        return "File not found", 404
    
    with open(filepath, 'r') as f:
        code = f.read()
    
    return render_template('shell.html', filename=filename, code=code)

io_managers = {}

@app.route('/run/<filename>', methods=['POST'])
def run_code(filename):
    filepath = os.path.join(DEPLOYMENT_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({'output': 'File not found'}), 404

    with open(filepath, 'r') as f:
        code = f.read()

    io_manager = IOManager()
    io_managers[filename] = io_manager

    def run_with_custom_io():
        with contextlib.redirect_stdout(io_manager), contextlib.redirect_stderr(io_manager):
            try:
                exec(code, {'input': io_manager.custom_input, 'print': io_manager.custom_print})
            except Exception as e:
                io_manager.custom_print(f"Error: {str(e)}")
        io_manager.output_queue.put(None)  # Signal that execution is complete

    threading.Thread(target=run_with_custom_io).start()

    return jsonify({'status': 'started'})

@app.route('/io/<filename>', methods=['POST'])
def handle_io(filename):
    if filename not in io_managers:
        return jsonify({'error': 'No running code found'}), 404

    io_manager = io_managers[filename]
    action = request.json['action']
    
    if action == 'output':
        try:
            output = io_manager.output_queue.get(timeout=0.1)
            if output is None:
                del io_managers[filename]
                return jsonify({'status': 'complete'})
            return jsonify({'status': 'continue', 'output': output})
        except queue.Empty:
            return jsonify({'status': 'waiting'})
    elif action == 'input':
        user_input = request.json['input']
        io_manager.input_queue.put(user_input)
        return jsonify({'status': 'continue'})

if __name__ == '__main__':
    os.makedirs(DEPLOYMENT_DIR, exist_ok=True)
    app.run(debug=True)