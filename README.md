# Galva AI


<details>
<summary>Directory Structure</summary>

```command
|   .env
|   .gitignore
|   process_uploads.py
|   README.md
|   requirements.txt
|   
+---app
|   |   .env
|   |   main.py
|   |   tas.log
|   |   test.db
|   |   
|   +---ai
|   |   |   gcp-ocr.py
|   |   |   openai_res.py
|   |   |   __init__.py
|   |           
|   +---data
|   |   +---merged_vector
|   |   \---pdfs
|   +---database
|   |   |   database.py
|   |   |   __init__.py
|   |   |   
|   |   +---crud
|   |   |   |   operations.py
|   |   |   |   pdf.py
|   |   |   |   user.py
|   |   |   |   __init__.py
|   |   |           
|   |   +---models
|   |   |   |   models.py
|   |   |   |   __init__.py
|   |   |           
|   |   +---schema
|   |   |   |   messages.py
|   |   |   |   pdf.py
|   |   |   |   user.py
|   |   |   |   __init__.py
|   |           
|   +---galva
|   |   |   business_logic.py
|   |   |   __init__.py
|   |           
|   +---lib
|   |   |   utils.py
|   |   |   __init__.py
|   |
|   +---routers
|   |   |   chat.py
|   |   |   pdf.py
|   |   |   user.py
|   |   |   __init__.py
|   |           
|   +---templates
|   |       admin_dashboard.html
|   |       chatbot.html
|   |       chatbot1.html
|   |       login.html
|   |       signup.html
|   |       user_dashboard.html
```
</details>

