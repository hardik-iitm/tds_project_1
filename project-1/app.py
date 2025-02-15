from datetime import datetime
import json
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
def sort_objects_in_file(file_path, sort_fields: list, target_output):
    try:
        # Load objects from the input file
        with open(file_path, 'r') as file:
            objects = json.load(file)

        # Ensure the file contains an array
        if not isinstance(objects, list):
            raise HTTPException(status_code=400, detail="The file does not contain an array of objects.")

        # Ensure each object contains the required fields for sorting
        for obj in objects:
            for field in sort_fields:
                if field not in obj:
                    raise HTTPException(status_code=400, detail=f"Field '{field}' not found in one or more objects.")

        # Sort objects based on the given fields
        sorted_objects = sorted(objects, key=lambda x: tuple(x[field] for field in sort_fields))

        # Write sorted objects to the output file
        with open(target_output, 'w') as file:
            json.dump(sorted_objects, file, indent=4)

        return {"message": f"Objects sorted and written to {target_output}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

# Task handler (this uses OpenAI to process tasks)
async def process_task(task: str) -> str:
    url = "http://aiproxy.sanand.workers.dev/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    
    COUNT_WEEKDAYS_TOOL={
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
                "time": {
                    "type": "string",
                    "description": "Meeting time in HH:MM format"
                },
                "meeting_room": {
                    "type": "string",
                    "description": "Name of the meeting room"
                }
            },
            "required": ["date", "time", "meeting_room"],
            "additionalProperties": False
        },
        "strict": True
    }
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
                    sort_fields = arguments['sort_fields']
                    target_output = arguments['target_output']
                    result = sort_objects_in_file(file_path, sort_fields, target_output)

                    return {"message": "Task successfully executed", "result": f"File at {file_path} sorted and written to {target_output}"}


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

