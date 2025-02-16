from datetime import datetime
import json
import shutil
import subprocess
import sys
from fastapi import FastAPI, HTTPException
import httpx
import os

# Initialize FastAPI app
app = FastAPI()

# Set your OpenAI API key (ensure it's securely handled)
OPENAI_API_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIyZjMwMDIyOTFAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9.DuTpd4IaEMZT5E5c2ZZgt7s2bhrpn5VOurdBiwZLK4s"
# Helper function to count weekdays in a file and write the result to an output file
def count_weekdays_in_file(file_path, target_weekday, target_output):
    weekday_map = {"Sunday": 6, "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5}
    weekday_count = 0

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    
    with open(file_path, "r") as file:
        for line in file:
            try:
                date_str = line.strip()
                date = datetime.strptime(date_str, '%Y-%m-%d')
                if date.weekday() == weekday_map.get(target_weekday):
                    weekday_count += 1
            except ValueError:
                continue  # Skip invalid date formats

    # Write the result to the target output file
    output_dir = os.path.dirname(target_output)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)  # Create the directory if it doesn't exist

    with open(target_output, "w") as file:
        file.write(str(weekday_count))

    return weekday_count

# Helper function to sort objects in the file
def sort_json_array(file_path, fields, target_path):
     # Read and load the JSON data from the file
    try:
        with open(file_path, 'r') as file:
            json_data = json.load(file)
    except FileNotFoundError:
        raise ValueError(f"File at {file_path} not found.")
    except json.JSONDecodeError:
        raise ValueError("Error decoding JSON from the file.")
    
    if not isinstance(json_data, list):
        raise ValueError("JSON data should be a list of dictionaries.")
    if not isinstance(fields, list):
        raise ValueError("fields should be provided as a list.")
    
     # Ensure the fields are valid (exist in the dictionary keys)
    for field in fields:
        if not all(field in item for item in json_data):
            raise ValueError(f"Field '{field}' not found in all items.")
        
    # Sort by the provided fields (ascending order by default)
    sorted_data = sorted(json_data, key=lambda x: tuple(x.get(field) for field in fields))

    # Write the result to the target output file
    output_dir = os.path.dirname(target_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)  # Create the directory if it doesn't exist

    with open(target_path, "w") as file:
        json.dump(sorted_data, file, indent=2)
    return sorted_data

def format_file_with_prettier(file_path, prettier_version, target_output):
    # Check if the file exists
    if not os.path.exists(file_path):
        return f"Error: The file at {file_path} does not exist."
    # Write the result to the target output file
    output_dir = os.path.dirname(target_output)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)  # Create the directory if it doesn't exist
    try:
        # Check if Prettier is already installed locally (node_modules should exist)
        if not os.path.exists("node_modules"):
            print("Installing Prettier locally...")
            # Install Prettier of the specified version
            subprocess.run(["npm", "install", f"prettier@{prettier_version}"], check=True, text=True, shell=True)

        
        # Use npx to run Prettier from the locally installed node_modules
        print(f"Formatting {file_path} using Prettier version {prettier_version}...")
        subprocess.run(["npx", f"prettier@{prettier_version}", "--write", file_path], shell=True, check=True)
        
        # Check if the source and target files are the same
        if os.path.abspath(file_path) != os.path.abspath(target_output):
            # Copy the formatted content to the target output file
            shutil.copy(file_path, target_output)  # Copy the formatted file to the target output
            return f"File at {file_path} has been formatted successfully with Prettier {prettier_version}, and copied to {target_output}."
        else:
            return f"File at {file_path} has been formatted successfully with Prettier {prettier_version}"

        return f"File at {file_path} has been formatted successfully with Prettier {prettier_version}."
    except subprocess.CalledProcessError as e:
        return f"Error: Could not format the file. {e}"

    except FileNotFoundError:
        return "Error: Prettier is not installed. Please install Prettier globally via `npm install -g prettier`."

def install_python_package(package_name, package_version):
    try:
        if package_version !="unspecified":
            package_to_install = f"{package_name}=={package_version}"
        else:
            package_to_install = package_name
        
        print(f"Installing {package_to_install}...")
        subprocess.run([sys.executable, "-m", "pip", "install", package_to_install], check=True, text=True, capture_output=True,shell=True)
        return f"{package_to_install} installed successfully."
    
    except subprocess.CalledProcessError as e:
        return f"Error occurred during installation: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"
    
def run_script_with_argument(url, argument):
    # Define the path where the script will output the data (e.g., '/data')
    output_dir = "/data"
    
    # Check if the output directory exists, if not, create it
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)  # Creates the directory if it doesn't exist
            print(f"Directory '{output_dir}' created successfully.")
        except OSError as e:
            print(f"Error creating directory '{output_dir}': {e}")
            return
        
     # Define the path to save the script
    script_path = "datagen.py"

    # Download the script from the provided URL
    try:
        process = subprocess.Popen(["curl","-o",script_path,url],stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell=True)
        stdout, stderr = process.communicate()
        print(f"Script downloaded successfully to {script_path}.")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while downloading the script: {e.stderr}")
        return
    
    # Run the script with the user's email as argument and set the working directory to /data
    try:
        # Specify the working directory where the script should output files
        subprocess.run(["uv", "run", script_path, argument], check=True, shell=True)
        print(f"Data generation script executed successfully, output in {output_dir}.")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running the script: {e}")
    return "Execution of script: successful"

# Task handler (this uses OpenAI to process tasks)
async def process_task(task: str) -> str:
    url = "http://aiproxy.sanand.workers.dev/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    # Define the request payload for the OpenAI API
    data = {
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": task}],
    "tools": [
    {
        "type": "function",
        "function": {
            "name": "count_weekdays_in_file",
            "description": "Count the number of weekdays in a given file and write the result to the output file",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path of the file to process."
                    },
                    "target_weekday": {
                        "type": "string",
                        "description": "The weekday to count (e.g., 'Monday')."
                    },
                    "target_output": {
                        "type": "string",
                        "description": "The path where the result should be written.."
                    }

                },
                "required": ["file_path","target_weekday","target_output"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sort_objects_in_file",
            "description": "Sort an array of objects in a given file by specified fields (e.g., field1, field2) and write the result to an output file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path of the JSON file containing an array of objects to sort."
                    },
                    "sort_fields": {
                        "type": "string",
                        "description": "List of fields (e.g., ['field1', 'field2']) to sort the objects by."
                    },
                    "target_output": {
                        "type": "string",
                        "description": "The path where the sorted objects should be written"
                    }

                },
                "required": ["file_path","sort_fields","target_output"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "format_file_with_prettier",
            "description": "Formats the specified file using Prettier",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path of the file to be formatted."
                    },
                    "prettier_version": {
                        "type": "string",
                        "description": "The version of Prettier to use (e.g., \"3.4.2\")."
                    },
                    "target_output": {
                        "type": "string",
                        "description": "The path where the formatted file should be saved. It is equal to the file path by default"
                    }

                },
                "required": ["file_path","prettier_version","target_output"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "install_python_package",
    #         "description": "Installs a python package with an optional version",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "package_name": {
    #                     "type": "string",
    #                     "description": "The name of the Python package to install."
    #                 },
    #                 "package_version": {
    #                     "type": "string",
    #                     "description": "The version of the package. Set it to \"unspecified\" if not mentioned"
    #                 }

    #             },
    #             "required": ["package_name","package_version"],
    #             "additionalProperties": False
    #         },
    #         "strict": True
    #     }
    # },
    {
        "type": "function",
        "function": {
            "name": "run_script_with_argument",
            "description": "Installs uv and runs a script along with an argument",
            "parameters": {
                "type": "object",
                "properties": {
                    "script_url": {
                        "type": "string",
                        "description": "URL to the Python script"
                    },
                    "argument": {
                        "type": "string",
                        "description": "The argument to be passed along while running the script"
                    }

                },
                "required": ["script_url","argument"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_a_file",
            "description": "Deleted a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_name": {
                        "type": "string",
                        "description": "name of file"
                    }

                },
                "required": ["file_name"],
                "additionalProperties": False
            },
            "strict": True
        }
    }
    ],
    "tool_choice": "auto",
    
}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data)

            # Check if the response is successful
            if response.status_code == 200:
                result = response.json()
                print(result)
                return result
            else:
                raise HTTPException(status_code=400, detail="Error from OpenAI API")

    except Exception as e:
        # General exception handling for unexpected errors
        raise HTTPException(status_code=500, detail=f"Task processing failed: {str(e)}")


# POST /run?task=<task description> - Executes the task and returns the result
@app.post("/run")
async def run_task(task: str):
    if not task:
        raise HTTPException(status_code=400, detail="No task description provided")

    try:
        # Process the task and get the result
        result = await process_task(task=task)
        # return {"message": "Task successfully executed", "result": result}
        response = result['choices'][0]['message']
        if "tool_calls" in response:
        # Check if the function call in the response is valid
            function_call = result['choices'][0]['message']['tool_calls'][0]['function']
            # arguments = result['choices'][0]['message']['tool_calls'][0]['function']['arguments']
            # arguments = json.loads(arguments)
            if function_call:
                arguments = result['choices'][0]['message']['tool_calls'][0]['function']['arguments']
                arguments = json.loads(arguments)
                if function_call['name'] == "count_weekdays_in_file":
                    file_path = arguments['file_path']
                    target_weekday = arguments['target_weekday']
                    target_output = arguments['target_output']
                    
                    # Call the count_weekdays_in_file function to process the task
                    weekday_count = count_weekdays_in_file(file_path, target_weekday, target_output)

                    return {"message": "Task successfully executed", "result": f"Found {weekday_count} {target_weekday}s and written to {target_output}"}
                
                if function_call["name"]=="sort_objects_in_file":
                    file_path = arguments['file_path']
                    sort_fields = arguments['sort_fields'].split(",")
                    target_output = arguments['target_output']
                    result = sort_json_array(file_path, fields=sort_fields, target_path=target_output)

                    return {"message": "Task successfully executed", "result": f"File at {file_path} sorted and written to {target_output}"}

                if function_call["name"]=="format_file_with_prettier":
                    file_path = arguments['file_path']
                    prettier_version = arguments['prettier_version']
                    target_output = arguments['target_output']
                    result = format_file_with_prettier(file_path,prettier_version,target_output)

                    return {"message": "Task successfully executed", "result": f"File at {file_path} formatted using Prettier{prettier_version} {target_output}"}
                
                if function_call["name"]=="install_python_package":
                    package_name = arguments['package_name']
                    package_version = arguments['package_version']
                    result = install_python_package(package_name, package_version)

                    return {"message": "Task successfully executed", "result": f"{result}"}
                
                if function_call["name"]=="run_script_with_argument":
                    url = arguments['script_url']
                    argument = arguments['argument']
                    install_python_package("uv","unspecified")
                    result = run_script_with_argument(url, argument)

                    return {"message": "Task successfully executed", "result": f"{result}"}
        return result['choices'][0]['message']['content']

    except HTTPException as e:
        # This will catch errors raised during OpenAI API call and return HTTP 400
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    except Exception as e:
        # This will catch any other errors (e.g., internal errors) and return HTTP 500
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# GET /read?path=<file path> - Returns the content of the specified file
@app.get("/read")
async def read_file(path: str):
    if not path:
        raise HTTPException(status_code=400, detail="File path is required")

    # Check if the file exists
    if not os.path.isfile(path):
        return {"error": "File not found"}, 404  # Return 404 if file does not exist
    
    try:
        # Read and return the file content
        with open(path, 'r') as file:
            file_content = file.read()
        return  "HTTP 200 OK", {"content": file_content}

    except Exception as e:
        # Catch any exceptions related to file reading and raise a 500 error
        raise HTTPException(status_code=500, detail=f"Error reading the file: {str(e)}")

