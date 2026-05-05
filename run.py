from app import create_app


# Just creates the app and runs it
app = create_app()

if __name__ == "__main__":
    app.run(debug=False)