from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("pokemon_form.html", {"request": request})

@app.post("/search", response_class=HTMLResponse)
async def search_pokemon(request: Request, pokemon_name: str = Form(...)):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"https://pokeapi.co/api/v2/pokemon/{pokemon_name.lower()}")
            response.raise_for_status()
            pokemon_data = response.json()

            pokemon_info = {
                "name": pokemon_data["name"].capitalize(),
                "types": [t["type"]["name"].capitalize() for t in pokemon_data["types"]],
                "moves": [m["move"]["name"].replace("-", " ").title() for m in pokemon_data["moves"][:10]],
                "sprites": {
                    "front_default": pokemon_data["sprites"]["front_default"],
                    "front_shiny": pokemon_data["sprites"]["front_shiny"],
                    "back_default": pokemon_data["sprites"]["back_default"],
                    "back_shiny": pokemon_data["sprites"]["back_shiny"]
                }
            }

            return templates.TemplateResponse("pokemon_result.html", {
                "request": request,
                "pokemon": pokemon_info,
                "error": None
            })
        except httpx.HTTPStatusError:
            return templates.TemplateResponse("pokemon_result.html", {
                "request": request,
                "pokemon": None,
                "error": f"Pokemon '{pokemon_name}' not found. Please try again."
            })
        except Exception as e:
            return templates.TemplateResponse("pokemon_result.html", {
                "request": request,
                "pokemon": None,
                "error": f"An error occurred: {str(e)}"
            })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
