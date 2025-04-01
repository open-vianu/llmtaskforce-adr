# llmtaskforce-adr
Assessing whether an ADR is already known based on product label information  Background


## Dependencies
- Python
- Docker


## Starting the App
 1. Create a virtual environment

 ```
 python3 -m venv venv
 ```

2. Start Streamlit app

 ```
 streamlit run app/app.py
 ```


 3. Start Ollama container
 ```
 docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
```