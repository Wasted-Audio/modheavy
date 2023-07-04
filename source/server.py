#create a web server using flask
from flask import Flask, request, render_template
from flask_socketio import SocketIO, emit, send
from caseconverter import snakecase
import configparser
import sys
import os
import shutil
import subprocess
import shlex
import base64
import re
import json
import hvcc


app = Flask(__name__)

#Disable caching
app.config['TEMPLATES_AUTO_RELOAD'] = True
socketio = SocketIO(app)

config = configparser.ConfigParser()


class Colours:
    purple = "\033[95m"
    cyan = "\033[96m"
    dark_cyan = "\033[36m"
    blue = "\033[94m"
    green = "\033[92m"
    yellow = "\033[93m"
    red = "\033[91m"
    bold = "\033[1m"
    underline = "\033[4m"
    end = "\033[0m"


pluginCategories = [
    "DelayPlugin",
    "DistortionPlugin",
    "DynamicsPlugin",
    "FilterPlugin",
    "GeneratorPlugin",
    "MIDIPlugin",
    "ModulatorPlugin",
    "ReverbPlugin",
    "SimulatorPlugin",
    "SpatialPlugin",
    "SpectralPlugin",
    "UtilityPlugin"
]

deviceList = [
    'modduox',
    'moddwarf'
]

@app.route("/", methods=["GET"])
def upload_page():
    return render_template(
        "index.html",
        categoryLength = len(pluginCategories),
        pluginCategories = pluginCategories,
        name = name,
        brand = brand,
        uri = uri,
        category = category,
        deviceLength = len(deviceList),
        deviceList = deviceList,
        device = device,
        ip = ip,
        inputs = inputs,
        outputs = outputs
    )

#create a route that accepts POST requests with file uploads and saves them to disk
@app.route("/", methods=["POST"])
def upload():
    global name, brand, uri, category, device, ip
    if request.method == "POST":
        type = None
        if request.files:
            filenames = []
            uploaded_files = request.files.getlist("files")

            # # check if we received exactly 2 files
            # if len(uploaded_files) != 2:
            #     socketio.emit('response', {
            #         'data': '''You must upload exactly 2 files: <strong>gen_exported.cpp</strong> and <strong>gen_exported.h</strong> for Gen or <strong>rnbo_source.cpp</strong> and <strong>description.json</strong> for RNBO'''})
            #     return "ok"

            #detect if the files are Gen or RNBO
            for file in uploaded_files:
                filenames.append(file.filename)

            rootDirectory = "/home/modgen/mod-plugin-builder/heavy-plugins/"
            prepareDirectory(rootDirectory)
            #create a new folder to save the files
            directory = f'{rootDirectory}plugins/heavy-plugin/'
            if not os.path.exists(directory):
                os.makedirs(directory)

            for file in uploaded_files:
                # # check if the file has one of the accepted filenames
                # if (type == 'gen' and file.filename not in acceptedGenFilenames) or (type == 'rnbo' and file.filename not in acceptedRnboFilenames):
                #     socketio.emit('response', {'data': 'Invalid filename: '+file.filename})
                #     return "ok"

                file.save(f'{directory}{file.filename}')


            socketio.emit('response', {'data': 'Files uploaded successfully', 'type': 'success'})


            # get the settings from the post form
            name = request.form.get('name')
            brand = request.form.get('brand')
            uri = request.form.get('uri')
            category = request.form.get('category')
            device = request.form.get('device')
            ip = request.form.get('ip')

            if request.form.get('save-settings') == 'true':
                saveSettings()

            meta_dict = {
                'name': name,
                'dpf': {
                    'project': True,
                    'dpf_path': '../../../',
                    'midi_input': 0,
                    'midi_output': 0,
                    'plugin_uri': uri,
                    'plugin_formats': [
                        'lv2'
                    ],
                    'lv2_info': f'lv2:{category}'
                }
            }

            with open(f'{directory}meta.json', 'w') as metajson:
                meta_object = json.dumps(meta_dict, indent=4)
                metajson.write(meta_object)

            socketio.emit('response', {'data': 'Write metadata file', 'type': 'success'})

            # export the plugin
            if exportPlugin(directory, name) is False:
                socketio.emit('response', {'data': 'Failed to export plugin', 'type': 'error'})
                return "ok"

            # build the plugin
            if buildPlugin(device, directory) is False:
                socketio.emit('response', {'data': 'Failed to build plugin', 'type': 'error'})
                return "ok"

            # compress the plugin
            if compressPlugin(brand, name, directory) is False:
                socketio.emit('response', {'data': 'Failed to compress plugin', 'type': 'error'})
                return "ok"

            if getBase64(directory) is False:
                socketio.emit('response', {'data': 'Failed to get base64', 'type': 'error'})
                return "ok"

        else:
            socketio.emit('response', {'data': 'No files were selected', 'type': 'error'})
        return "ok"
    else:
        return "not a post request"

#create a route that accepts GET requests and returns a list of files in the current directory
@app.route("/files", methods=["GET"])
def files():
    import os
    files = os.listdir()
    return str(files)

@socketio.on('connect')
def test_connect():
    emit('response', {'data': 'Connected'})

def prepareDirectory(directory):
    # delete existing files and folders in the directory
    dirList = ['plugins', 'custom-ttl','presets','bin']
    for dir in dirList:
        _dir_path = f'{directory}{dir}'
        if os.path.exists(_dir_path):
            for filename in os.listdir(_dir_path):
                file_path = os.path.join(_dir_path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    socketio.emit('response', {'data': f'Failed to delete {file_path}. Reason: {e}', type: 'error'})

def compressPlugin(brand, name, directory):
    # build the plugin
    exportPath = f'{directory}bin/{name}.lv2'
    socketio.emit('response', {'data': 'Compressing Plugin'})
    if not os.path.exists(exportPath):
        socketio.emit('response', {'data': 'Plugin not found', 'type': 'error'})
        return False
    # rename the plugin
    pluginName = f'{snakecase(brand)}-{snakecase(name)}.lv2'
    pluginPath = f'{directory}bin/{pluginName}'
    os.rename(exportPath, pluginPath)
    command = f'tar zhcf heavy-plugin.tar.gz {pluginName}'
    try:
        process = subprocess.Popen(
            shlex.split(command),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=f'{directory}bin'
            )
    except:
        socketio.emit('response', {'data': f'ERROR {sys.exc_info()[1]} while running {command}', 'type': 'error'})
        return False
    while True:
        output = process.stdout.readline()
        errors = process.stderr.readline()
        if process.poll() is not None:
            break
        if output:
            socketio.emit('response', {'data': output.strip().decode(), 'type': 'info'})
        if errors:
            socketio.emit('response', {'data': errors.strip().decode(), 'type': 'error'})
            return False
    socketio.emit('response', {'data': 'Plugin compressed successfully', 'type': 'success'})
    return True

#convert the tar to base64 and send it to the client

def getBase64(directory):
    if not os.path.exists(f'{directory}bin/heavy-plugin.tar.gz'):
        socketio.emit('response', {'data': 'Compressed plugin file not found', 'type': 'error'})
        return False
    with open(f'{directory}/bin/heavy-plugin.tar.gz', 'rb') as file:
        encoded = base64.encodebytes(file.read()).decode('utf-8')
        socketio.emit('response', {'data': encoded, 'type': 'plugin'})
    return True

def saveSettings():
    config['Default']['name'] = name
    config['Default']['brand'] = brand
    config['Default']['uri'] = uri
    config['Default']['category'] = category
    config['Default']['device'] = device
    config['Default']['ip'] = ip
    config['Default']['inputs'] = inputs
    config['Default']['outputs'] = outputs

    with open('settings.ini', 'w') as configfile:
        config.write(configfile)

def exportPlugin(directory, name):
    # export the plugin
    socketio.emit('response', {'data': 'Exporting Plugin code'})

    try:
        results = hvcc.compile_dataflow(
            f'{directory}main.pd',
            f'{directory}',
            name,
            f'{directory}meta.json',
            [],
            ['dpf'],
            True
        )
    except:
        socketio.emit('response', {'data': f'ERROR {sys.exc_info()[1]} while running hvcc', 'type': 'error'})
        return False

    errorCount = 0
    for r in list(results.values()):
        # print any errors
        if r["notifs"].get("has_error", False):
            for i, error in enumerate(r["notifs"].get("errors", [])):
                errorCount += 1
                socketio.emit('response', {'data': "{4:3d}) {2}Error{3} {0}: {1}".format(
                    r["stage"], error["message"], Colours.red, Colours.end, i + 1)
                    })

            # only print exception if no errors are indicated
            if len(r["notifs"].get("errors", [])) == 0 and r["notifs"].get("exception", None) is not None:
                errorCount += 1
                socketio.emit('response', {'data': "{2}Error{3} {0} exception: {1}".format(
                    r["stage"], r["notifs"]["exception"], Colours.red, Colours.end)
                })

            # clear any exceptions such that results can be JSONified if necessary
            r["notifs"]["exception"] = []

        # print any warnings
        for i, warning in enumerate(r["notifs"].get("warnings", [])):
            socketio.emit('response', {'data': "{4:3d}) {2}Warning{3} {0}: {1}".format(
                r["stage"], warning["message"], Colours.yellow, Colours.end, i + 1)
            })

    if errorCount > 1:
        return False

    socketio.emit('response', {'data': 'Plugin exported successfully', 'type': 'success'})
    return True

def buildPlugin(device, directory):
    # build the plugin
    socketio.emit('response', {'data': f'Building Plugin for {device} in {directory}'})
    command = f'make {device}'
    try:
        process = subprocess.Popen(
            shlex.split(command),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=directory,
            executable='/bin/bash'
            )
    except:
        socketio.emit('response', {'data': f'ERROR {sys.exc_info()[1]} while running {command}', 'type': 'error'})
        return False

    while True:
        output = process.stdout.readline()
        errors = process.stderr.readline()
        if process.poll() is not None:
            break
        if output:
            socketio.emit('response', {'data': output.strip().decode(), 'type': 'build'})
        if errors:
            socketio.emit('response', {'data': errors.strip().decode(), 'type': 'warning'})
    socketio.emit('response', {'data': 'Plugin built successfully', 'type': 'success'})
    return True

#if the settings.ini file does not exist, create it with some default values
if not os.path.exists('settings.ini'):
    config['Default'] = {}
    name = 'ExampleName'
    brand = 'ExampleBrand'
    uri = 'http://example.com/example'
    category = 'UtilityPlugin'
    device = 'moddwarf'
    ip = '192.168.51.1'
    inputs = '2'
    outputs = '2'
    saveSettings()
else:
    config.read('settings.ini')
    name = config['Default']['name']
    brand = config['Default']['brand']
    uri = config['Default']['uri']
    category = config['Default']['category']
    device = config['Default']['device']
    ip = config['Default']['ip']
    inputs = config['Default'].get('inputs','2')
    outputs = config['Default'].get('outputs','2')

if __name__ == "__main__":
    print('Starting server...')
    socketio.run(app, host='0.0.0.0', allow_unsafe_werkzeug=True)
