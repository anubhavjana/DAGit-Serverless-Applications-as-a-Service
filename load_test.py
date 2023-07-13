import requests
import concurrent.futures

# Define the URL and parameters
url = "http://10.129.28.219:5001/run/text_sentiment_analysis_trigger"
params = {
    "url": "https://en.wikipedia.org/wiki/Mathematics"
}

# Function to send a request
def send_request(url, params):
    response = requests.post(url, json=params)
    return response.json()

# Number of parallel requests
num_requests = 500

# Create a ThreadPoolExecutor
executor = concurrent.futures.ThreadPoolExecutor()

# Submit the requests in parallel
futures = [executor.submit(send_request, url, params) for _ in range(num_requests)]

# Wait for all the requests to complete
concurrent.futures.wait(futures)

status = []
# Process the responses
for future in futures:
    response = future.result()
    # Process the response as needed
    status.append(response["status"])

print(status)

success_count = status.count(200)

if(num_requests ==  success_count):
    print("Success")
else:
    print("Failure")
