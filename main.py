

if __name__ == "__main__":
    import uvicorn
    try:
        uvicorn.run("src.app:app", host="127.0.0.1", port=8000, reload=True, log_level="debug")
    except KeyboardInterrupt as e:
        raise Exception("El proceso fue interrumpido: ", e)