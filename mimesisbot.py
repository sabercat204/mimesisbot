import irc.client
import nltk
import pickle
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import time
import random
import shutil
import psutil

# Set up NLTK for basic natural language processing
nltk.download('punkt')

# Function to train or load the chatbot model
def train_or_load_model():
    try:
        with open("chatbot_model.pkl", "rb") as file:
            return pickle.load(file)
    except FileNotFoundError:
        print("Model not found. Training a new model.")
        return nltk.chat.Chat("local_storage")

# Function to save the chatbot model
def save_model(model):
    with open("chatbot_model.pkl", "wb") as file:
        pickle.dump(model, file)

# Function to add a user to the system
def add_user(username, password):
    user_data[username] = {
        'password': password,
        'prompt_history': [],
    }
    print(f"User '{username}' added.")

# Function to authenticate the user
def authenticate_user(username, password):
    if username in user_data and user_data[username]['password'] == password:
        return True
    else:
        print("Authentication failed.")
        return False

# Function to generate a response using the chatbot model
def generate_response(model, user_input):
    return model.respond(user_input)

# Function to mimic the user's writing style and generate a response
def mimic_user_style(user_data, target_user, user_input):
    # Get the prompt history of the target user
    target_user_history = user_data.get(target_user, {}).get('prompt_history', [])

    # Combine user's input with target user's prompt history
    combined_text = " ".join([user_input] + target_user_history)

    # Use CountVectorizer to convert text into a matrix of token counts
    vectorizer = CountVectorizer()
    matrix = vectorizer.fit_transform([combined_text] + target_user_history)

    # Calculate cosine similarity between user's input and target user's history
    similarities = cosine_similarity(matrix)

    # Find the index of the most similar prompt in target user's history
    most_similar_index = similarities[0].argsort()[-2]

    # Mimic the writing style of the target user
    mimic_response = target_user_history[most_similar_index]

    return mimic_response

# Function to train the bot from multiple users simultaneously
def train_chimera(usernames):
    global chatbot_model

    # Training data for the chimera persona
    training_data = []

    for username in usernames:
        # Get the prompt history of each user
        user_history = user_data.get(username, {}).get('prompt_history', [])

        # Add the user's prompt history to the training data
        training_data.extend(user_history)

    # Train the chatbot model with the combined training data
    chatbot_model.train(training_data)

    print(f"Chimera persona trained from users: {', '.join(usernames)}")

# Function to list statistics relevant to training data variables
def list_training_statistics():
    global user_data

    total_users = len(user_data)
    total_messages = sum(len(history['prompt_history']) for history in user_data.values())

    print(f"Total Users: {total_users}")
    print(f"Total Messages: {total_messages}")

# Function to list system-related statistics
def list_system_statistics():
    print("System Statistics:")

    # Storage usage on the host
    total, used, free = shutil.disk_usage("/")
    print(f"Total Storage: {total / (2**30):.2f} GB")
    print(f"Used Storage: {used / (2**30):.2f} GB")
    print(f"Free Storage: {free / (2**30):.2f} GB")

    # Memory usage on the host
    memory = psutil.virtual_memory()
    print(f"Total Memory: {memory.total / (2**30):.2f} GB")
    print(f"Used Memory: {memory.used / (2**30):.2f} GB")
    print(f"Free Memory: {memory.free / (2**30):.2f} GB")

    # CPU usage on the host
    cpu_percent = psutil.cpu_percent()
    print(f"CPU Usage: {cpu_percent}%")

    return total, used, memory.percent, cpu_percent

# Function to check resource usage and throttle if necessary
def check_resource_usage():
    total_storage, used_storage, memory_percent, cpu_percent = list_system_statistics()

    # Throttle if storage, memory, or CPU usage exceeds 75%
    if used_storage / total_storage > 0.75 or memory_percent > 75 or cpu_percent > 75:
        print("Resource usage exceeds 75%. Throttling the bot.")
        return True
    else:
        return False

# Initialize user data
user_data = {}

# Load or train the chatbot model
chatbot_model = train_or_load_model()

# Initialize random output interval (default to 5 minutes)
random_output_interval = 5 * 60

# Timestamp for the last random output
last_random_output_time = time.time()

# IRC Bot class
class IRCBot(irc.client.SimpleIRCClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mimesis_mode = False  # Mimesis mode is initially off

    def on_welcome(self, connection, event):
        print(f"Connected to {event.arguments[0]}")
        connection.join("#your_channel")  # Replace with the desired channel

    def on_pubmsg(self, connection, event):
        global chatbot_model
        global last_random_output_time

        # Extract sender and message from IRC message
        sender = event.source.nick
        message = event.arguments[0]

        # Check if the message is an admin command
        if sender == "admin" and message.startswith("!train"):
            _, nickname = message.split(" ", 1)
            self.train_bot(nickname)

        # Check if the message is an admin command to mimic a user
        elif sender == "admin" and message.startswith("!mime"):
            _, target_user, _ = message.split(" ", 2)
            self.mimic_user_conversation(sender, target_user)

        # Check if the message is an admin command to toggle mimesis mode
        elif sender == "admin" and message.startswith("!admin mimesis"):
            _, mode = message.split(" ", 3)
            self.toggle_mimesis_mode(mode.lower())

        # Check if the message is an admin command to set random output interval
        elif sender == "admin" and message.startswith("!admin random_output"):
            _, interval_minutes = message.split(" ", 3)
            self.set_random_output_interval(int(interval_minutes))

        # Check if the message is an admin command to train the chimera persona
        elif sender == "admin" and message.startswith("!admin train_chimera"):
            _, usernames_str = message.split(" ", 3)
            usernames = [username.strip() for username in usernames_str.split(',')]
            self.train_chimera(usernames)

        # Check if the message is an admin command to list training statistics
        elif sender == "admin" and message.startswith("!admin training_statistics"):
            self.list_training_statistics()

        # Check if the message is an admin command to list system statistics
        elif sender == "admin" and message.startswith("!admin system_statistics"):
            self.list_system_statistics()

        # Check if the message is a user message
        elif sender in user_data:
            self.process_user_message(sender, message)

    def toggle_mimesis_mode(self, mode):
        if mode == "on":
            self.mimesis_mode = True
            print("Mimesis mode is ON.")
        elif mode == "off":
            self.mimesis_mode = False
            print("Mimesis mode is OFF.")
        else:
            print("Invalid mimesis mode. Use '!admin mimesis on' or '!admin mimesis off'.")

    def train_chimera(self, usernames):
        global chatbot_model
        self.train_chimera(usernames)

    def train_bot(self, nickname):
        global chatbot_model

        # Use the chatbot model to generate a response
        response = chatbot_model.respond("Hello!")

        # Save the training data to a file with the user's nickname as the base
        filename = f"{nickname}_training_data.txt"
        with open(filename, "a") as file:
            file.write(response)
            print(f"Training data saved to {filename}")

    def mimic_user_conversation(self, sender, target_user):
        global user_data

        # Get the prompt history of the target user
        target_user_history = user_data.get(target_user, {}).get('prompt_history', [])

        # Mimic the entire conversation of the target user
        mimic_responses = [f"(as {target_user}): {msg}" for msg in target_user_history]

        # Print the mimicked responses
        for response in mimic_responses:
            print(f"Bot {response}")
            self.connection.privmsg("#your_channel", response)

    def process_user_message(self, sender, message):
        global chatbot_model
        global user_data

        # Check resource usage before responding
        if check_resource_usage():
            # Send a warning message to the admin
            self.connection.privmsg("admin", "Warning: Resource usage exceeds 75%. Bot has been throttled.")

            # Throttle the bot by delaying the response
            time.sleep(5)
        else:
            # Use the chatbot model to generate a response
            response = chatbot_model.respond(message)

            # If in mimesis mode, don't identify the user
            if self.mimesis_mode:
                print(f"Bot (as $user): {response}")
                self.connection.privmsg("#your_channel", f"(as $user): {response}")
            else:
                # Print the bot's response
                print(f"Bot: {response}")
                self.connection.privmsg("#your_channel", f"Bot: {response}")

            # Update user's prompt history
            user_data[sender]['prompt_history'].append(message)

    def on_disconnect(self, connection, event):
        print("Disconnected.")

# Create IRC connection and bot instance
client = irc.client.IRC()
bot = IRCBot()

# Set up IRC connection
server = "irc.server.com"  # Replace with the IRC server address
port = 6667
nickname = "your_bot_nickname"
channel = "#your_channel"  # Replace with the desired channel

connection = client.server().connect(server, port, nickname)

# Start the IRC bot
client.process_forever()
