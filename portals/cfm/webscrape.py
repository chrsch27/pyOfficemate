from typing import Any
from flask import Flask, jsonify, request
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from urllib.parse import unquote, urlparse
import os
import logging
import openai
from openai.resources.beta.threads.messages import Messages
import assistant
import time
import json


logging.basicConfig(level=logging.INFO)

print(selenium.__version__)
app = Flask(__name__)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
  raise ValueError("No OpenAI API key found in environment variables")
client = openai.OpenAI(api_key=OPENAI_API_KEY)
assistant_id = assistant.create_assistant(client)

def start_gptAssistant(message):
  #core_functions.check_api_key()  # Check the API key
  logging.info("Starting a new conversation...")
  #message_File_IDs.clear() 
  user_input = message

  thread = client.beta.threads.create(
    messages=[
      {
        "role": "user",
        "content": user_input,
        "attachments": [
        ]
      }
    ]
  )
  logging.info(f"New thread created with ID: {thread.id}")
  return thread.id
  

def chat_gptAssistant(thread_id,user_input=None):
  if not thread_id:
    logging.error("Error: Missing thread_id")
    return jsonify({"error": "Missing thread_id"}), 400
  logging.info(f"Chat gestartet mit ThreadId: {thread_id}")

  if user_input is not None:  
    message = client.beta.threads.messages.create(
        thread_id=thread_id, 
        role="user",
        content=user_input
    )
  run = client.beta.threads.runs.create(thread_id=thread_id,
                                        assistant_id=assistant_id)
  return (run.id)
  

def check_gptAssistant(thread_id, run_id):
  if not thread_id or not run_id:
    print("Error: Missing thread_id or run_id in /check")
    return {"response": "error"}
  return check_run_status(thread_id, run_id)



def check_run_status(thread_id, run_id):
  start_time = time.time()
  run_status = client.beta.threads.runs.retrieve(thread_id=thread_id,
     run_id=run_id)
  while time.time() - start_time <60:

    print("Checking run status:", run_status.status)

    if run_status.status == 'completed':
      logging.info("---------- RESPONSE -------------")
      logging.info(run_status)
      messages = client.beta.threads.messages.list(thread_id=thread_id)
      message_content = messages.data[0].content[0].text
      logging.info(f"Assistant response: {message_content}")
      # Remove annotations
      #annotations = message_content.annotations
      #for annotation in annotations:
        #message_content.value = message_content.value.replace(
            #annotation.text, '')
      print("Run completed, returning response")
      return {
          "response": message_content.value,
          "status": "completed",
          "runid": run_id
      }

    time.sleep(5)
    run_status = client.beta.threads.runs.retrieve(thread_id=thread_id,
       run_id=run_id)

  print("Action in progress...")
  return {"response": "running", "status": run_status.status,
                 "runid": run_id}


@app.route('/startGPT', methods=['POST'])
def start_conversation(message):
  #core_functions.check_api_key()  # Check the API key
  logging.info("Starting a new conversation...")
  #message_File_IDs.clear() 
  data = request.json
  user_input = data.get('message', '')
  return jsonify({"thread_id": start_gptAssistant(message)})




@app.route('/chat', methods=['POST'])
def chat():

  data = request.json
  user_input = data.get('message', 'Please return all data')
  thread_id = data.get('thread_id')
  #user_input = data.get('message', '')
  logging.info(f"Received user input: {user_input}")
  #message_File_IDs.append(upload_to_openai(file_path))
  print("MESSAGE-FILE-IDS: ", message_File_IDs)

  if not thread_id:
    logging.error("Error: Missing thread_id")
    return jsonify({"error": "Missing thread_id"}), 400

  message = client.beta.threads.messages.create(
      thread_id=thread_id, 
      role="user",
      content=user_input
  )
  run = client.beta.threads.runs.create(thread_id=thread_id,
                                        assistant_id=assistant_id)
  # This processes any possible action requests
  return jsonify({"run_id": run.id})
  #core_functions.process_tool_calls(client, thread_id, run.id, tool_data)

  #messages = client.beta.threads.messages.list(thread_id=thread_id)
  #delete_message_files(message_File_IDs)
  #logging.info(f"Response Message: {messages}")
  #response = messages.data[0].content[0].text.value
  #logging.info(f"Assistant response: {response}")
  #return jsonify({"response": response})

# Check status of run

@app.route('/check', methods=['POST'])
def check():
  print(request.json)
  data = request.json
  thread_id = data.get('thread_id')
  run_id = data.get('run_id')
  return check_gptAssistant(thread_id, run_id)

@app.route('/downloadFiles', methods=['GET'])
def find_and_download_pdfs():
  url = request.args.get('url')
  if not url:
      return jsonify({"error": "Please provide a valid URL parameter."}), 400

  chrome_options = Options()
  chrome_options.add_argument("--headless=new")
  chrome_options.add_argument("--no-sandbox")
  chrome_options.add_argument("--disable-dev-shm-usage")
  chrome_options.add_argument("--disable-gpu")
  driver = webdriver.Chrome(options=chrome_options)
  logging.info("Starting the webdriver...")
  downloads = []
  try:
      driver.get(url)
      WebDriverWait(driver, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
      logging.info("Webdriver loaded the page.")
      try:
        # Warte darauf, dass mindestens ein Attachment-Element auftaucht
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "attachment"))
        )
      except TimeoutException:
        logging.info("Timeout: Keine Download-Elemente gefunden.")
        return jsonify({"downloads": []})


    
      download_elements = driver.find_elements(By.TAG_NAME, 
          "attachment")
      
      logging.info(f"Found {len(download_elements)} download elements---------------")
      #logging.info(f"Download elements: {download_elements}")
      for element in download_elements:
        # Extrahiere den Titel/Dateinamen
        title_element = element.find_element(By.CSS_SELECTOR, "name.cursor-hand")
        filename = title_element.text

        logging.info(f"Found download element with filename: {filename}")
        # Extrahiere das Datum
        date_element = element.find_element(By.TAG_NAME, "date")
        upload_date = date_element.text

        original_window = driver.current_window_handle
        old_handles = driver.window_handles
        logging.info (f"Upload Date: {upload_date}")
        downloadDoc_element = element.find_element(By.CSS_SELECTOR, "grid.clickable")
        #logging.info(f"DownloadDoc_element: {downloadDoc_element}")
        downloadDoc_element.click()

        WebDriverWait(driver, 10).until(
          lambda driver: len(driver.window_handles) > len(old_handles)
        )

        # Wechsle zum neuen Tab
        new_window = [handle for handle in driver.window_handles if handle != original_window][0]
        driver.switch_to.window(new_window)
        
        # Hole URL
        download_url = driver.current_url
        driver.close()
        driver.switch_to.window(original_window)
        file_content=''
        #response = requests.get(download_url)
        #response.raise_for_status()  # Überprüft, ob der Request erfolgreich war

        # Den Inhalt als Bytes in einer Variable speichern:
        #file_content = response.content
        #logging.info(f"File content: {file_content}")
        filename = extract_filename(download_url)
        logging.info(f"Extracted filename: {filename}")
        
        downloads.append({
            'filename': filename,
            'upload_date': upload_date,
            'url' : download_url,
            'content': file_content
        })
  except Exception as e:
    if str(e).startswith("Message: no such window:"):
        return jsonify({"downloads": []}), 200
    return jsonify({"error": str(e)}), 500


  finally:
      driver.quit()
  logging.info(f"Found {len(downloads)} PDFs.===============================")
  logging.info(f"Downloaded PDFs: {downloads}")
  return jsonify({"downloads": downloads})


def extract_filename(url):
  # URL parsen
  parsed_url = urlparse(url)
  logging.info(f"Parsed URL: {parsed_url}")
  # Den Pfad extrahieren und den letzten Teil (Dateinamen) herausfiltern
  path = parsed_url.path
  filename = os.path.basename(path)
  # Falls URL-kodierte Zeichen enthalten sind, diese decodieren
  logging.info(f"Filename: {filename}")
  return unquote(filename)


@app.route('/scrape', methods=['GET'])
def scrape():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "Please provide a valid URL parameter."}), 400

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(url)
        time.sleep(10)  # Ggf. durch explizite Waits ersetzen
        print (driver.title)

        content_elements = driver.find_elements(By.CSS_SELECTOR, "content.answer-inquiry-content")
        section_elements = driver.find_elements(By.CSS_SELECTOR, "section.inquiry-item")

        answer_inquiry_list = [elem.text.strip() for elem in content_elements]
        inquiry_items_list   = [elem.text.strip() for elem in section_elements]

        data = {
            "answer_inquiry_content": answer_inquiry_list,
            "inquiry_items": inquiry_items_list
        }
        thread_id=start_gptAssistant(json.dumps(data))
        run_id=chat_gptAssistant(thread_id)
        completed=False;
        result={}
        logging.info(data)
        while not completed:
          result = check_gptAssistant(thread_id, run_id)
          completed = result["status"] == "completed"
          if not completed:
            logging.info(f"Run status: {result['status']}")
            time.sleep(4)
        logging.info(f"Run completed with status: {result['status']}")
        logging.info(f"Response: {result['response']}")
           
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        driver.quit()




if __name__ == '__main__':
    app.run(debug=True, port=5000)
