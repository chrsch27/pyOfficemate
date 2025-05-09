from typing import Any
from flask import Flask, jsonify, request
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import ElementClickInterceptedException
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

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
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

def wait_for_element_count_stabilization(driver, selector, timeout=30, stable_time=3):
    """Wait until the count of elements matching the selector stops changing."""
    start_time = time.time()
    last_count = 0
    last_change_time = start_time

    while time.time() - start_time < timeout:
        current_count = len(driver.find_elements(By.CSS_SELECTOR, selector))

        if current_count != last_count:
            # Count changed, reset the stable timer
            last_count = current_count
            last_change_time = time.time()
        elif time.time() - last_change_time >= stable_time:
            # Count has been stable for the required time
            return current_count

        time.sleep(0.5)

    # Timeout reached, return whatever we have
    return last_count

@app.route('/scrape', methods=['GET'])
def scrape():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "Please provide a valid URL parameter."}), 400

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080") 
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(url)
        logging.info(f"Navigated to URL: {url}")

        # Wait for sections to load
        wait = WebDriverWait(driver, 30)
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "section.inquiry-item")))
        logging.info("Section elements found")

        element_count = wait_for_element_count_stabilization(driver, "section.inquiry-item")
        logging.info(f"Found {element_count} stable section elements")
        section_elements = driver.find_elements(By.CSS_SELECTOR, "section.inquiry-item")

        content_elements = driver.find_elements(By.CSS_SELECTOR, "content.answer-inquiry-content")
        

        answer_inquiry_list = [elem.text.strip() for elem in content_elements]
        inquiry_items_list = [elem.text.strip() for elem in section_elements]
        logging.info(f"Found {len(content_elements)} content elements and {len(section_elements)} section elements")

        inquiry_details = []
        for i, item in enumerate(section_elements):
            logging.info(f"Processing section {i+1}/{len(section_elements)}")
            try:
                # Find all clickable elements
                buttons = item.find_elements(By.CLASS_NAME, "clickable")
                logging.info(f"Found {len(buttons)} clickable elements in section {i+1}")
                details_button = next((btn for btn in buttons if "Details" in btn.text), None)
                logging.info(f"Details button found: {details_button is not None}")

                if details_button:
                    logging.info(f"Found Details button in section {i+1}")
                    try:
                        # Try using JavaScript to click the button to avoid interception issues
                        driver.execute_script("arguments[0].click();", details_button)
                        logging.info("Clicked Details button using JavaScript")

                        # Wait for modal to open
                        time.sleep(2)

                        # First look for grid-cell with class "item-description"
                        description_cell = None
                        try:
                            description_cell = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "grid-cell.item-description")))
                            logging.info("Found item-description grid cell")
                        except Exception:
                            logging.warning(f"Could not find grid-cell.item-description in section {i+1}")

                        # If found, look for the value element inside it
                        value_text = None
                        if description_cell:
                            try:
                                # Try to find the value element inside the description cell
                                value_elem = description_cell.find_element(By.TAG_NAME, "value")
                                value_text = value_elem.text.strip()
                                logging.info(f"Found value element with text: {value_text[:30]}...")
                                inquiry_details.append(value_text)
                            except Exception as e:
                                logging.warning(f"Could not find value element: {str(e)}")
                                inquiry_details.append(f"Found item-description but no value element in section {i+1}")
                        else:
                            # Fallback to the original approach
                            possible_selectors = [".item-description", "div.modal-content", "div.modal-body", ".modal-dialog"]
                            modal_content = None

                            for selector in possible_selectors:
                                try:
                                    modal = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
                                    modal_content = modal.text.strip()
                                    logging.info(f"Found modal content using selector: {selector}")
                                    break
                                except Exception:
                                    continue

                            if modal_content:
                                inquiry_details.append(f"Full modal content (no value element found): {modal_content}")
                            else:
                                inquiry_details.append(f"Modal found but no content extracted in section {i+1}")

                        # Close modal - try multiple approaches
                        try:
                            # Try to find close button with various selectors
                            close_selectors = [
                                ".//button[contains(@class, 'close')]", 
                                ".//button[contains(text(), 'Close')]",
                                ".//button[contains(text(), 'Cancel')]", 
                                ".close", 
                                "[data-dismiss='modal']"
                            ]

                            close_button = None
                            for selector in close_selectors:
                                try:
                                    if selector.startswith(".//"):
                                        close_button = driver.find_element(By.XPATH, selector)
                                    else:
                                        close_button = driver.find_element(By.CSS_SELECTOR, selector)
                                    break
                                except:
                                    continue

                            if close_button:
                                driver.execute_script("arguments[0].click();", close_button)
                                logging.info("Clicked close button")
                            else:
                                # Click outside the modal or use Escape key
                                driver.execute_script("document.body.click();")
                                logging.info("Clicked outside modal")

                            time.sleep(1)  # Brief pause to let modal close
                        except Exception as e:
                            logging.warning(f"Error closing modal: {str(e)}")
                    except ElementClickInterceptedException:
                        logging.warning(f"Button in section {i+1} was intercepted, trying to scroll to it")
                        driver.execute_script("arguments[0].scrollIntoView(true);", details_button)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", details_button)
                    except Exception as e:
                        inquiry_details.append(f"Error clicking Details button in section {i+1}: {str(e)}")
                else:
                    inquiry_details.append(f"No Details button found in section {i+1}")
            except Exception as e:
                inquiry_details.append(f"Error processing section {i+1}: {str(e)}")

        logging.info(f"Inquiry details: {inquiry_details}")


        data = {
            "answer_inquiry_content": answer_inquiry_list,
            "inquiry_items": inquiry_items_list,
            "inquiry_details": inquiry_details
        }
        #return jsonify(data)
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