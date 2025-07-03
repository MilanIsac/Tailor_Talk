from fastapi import FastAPI, Request
from backend.agent import chat_with_agent
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post('/chat')
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        print("Backend received:", data)
        msg = data.get('message')
        session_id = data.get('session_id')
        response = chat_with_agent(msg, session_id)
        print("Backend sending:", {"response": response})
        return {'response': response}
    except Exception as e:
        print("Backend error:", e)
        return JSONResponse(content=
        {"response": "Sorry, there was an error processing your request. Please try again later."}, 
        status_code=500)
