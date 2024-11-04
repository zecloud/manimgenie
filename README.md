# AI Agent Video Generator with Manim

## Description
This project is an AI-powered application that generates educational mathematics/computer science videos using Manim (Mathematical Animation Engine). It leverages Azure OpenAI, Chainlit for the chat interface, and LangChain for AI model integration.

## Features
- 🤖 AI-powered code generation for Manim scenes
- 🎥 Automatic video generation from code
- 💬 Interactive chat interface
- 🔄 Asynchronous video processing
- 📥 Automatic video download and display

## Prerequisites
- Python 3.8+
- Azure OpenAI API access
- Manim installation

## Environment Variables
Create a .env file in the root directory of the project and add the following environment variables:
```bash
AZUREOPENAIAPIKEY=your_azure_openai_api_key
AZRESOURCE_NAME=your_azure_resource_name
AZDEPLOYMENT_NAME=your_azure_deployment_name
AZSESSIONPOOLURL=your_session_pool_url
```

## Usage
Set up your environment variables
Start the Chainlit application:
```bash
chainlit run app.py
```

### How it Works
User submits a question through the Chainlit interface
Azure OpenAI generates Manim code
Code is executed in a Python REPL session
Generated video is downloaded and displayed in the chat
Project Structure
app.py: Main application file
requirements.txt: Project dependencies
.env: Environment variables configuration

### Dependencies
chainlit
langchain
langchain-openai
langchain-community
azure-identity
manim

### Contributing
Contributions, issues, and feature requests are welcome!

### License
[Add your license here] 
