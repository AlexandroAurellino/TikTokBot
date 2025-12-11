from web import create_app, socketio

# Create the application
app = create_app()

if __name__ == '__main__':
    print("=" * 60)
    print(">>> AI Scene Changer - Modular Edition <<<")
    print(">>> Open: http://127.0.0.1:5000 <<<")
    print("=" * 60)
    
    # Run the server
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)