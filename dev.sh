#!/bin/bash

# baseCamp Development Server
# Runs both backend (FastAPI) and frontend (React/Vite) simultaneously

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to handle cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Stopping development servers...${NC}"
    # Kill all child processes
    jobs -p | xargs -r kill
    exit 0
}

# Set trap to handle Ctrl+C
trap cleanup SIGINT

echo -e "${GREEN}Starting baseCamp Development Environment${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}\n"

# Check if we're in the right directory
if [ ! -f "src/main.py" ]; then
    echo -e "${RED}Error: src/main.py not found. Please run this script from the baseCamp root directory.${NC}"
    exit 1
fi

if [ ! -d "frontend" ]; then
    echo -e "${RED}Error: frontend directory not found. Please run this script from the baseCamp root directory.${NC}"
    exit 1
fi

# Start backend server
echo -e "${BLUE}[BACKEND]${NC} Starting FastAPI server on http://localhost:8000"
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Give backend a moment to start
sleep 2

# Start frontend server
echo -e "${GREEN}[FRONTEND]${NC} Starting Vite dev server on http://localhost:5173"
cd frontend && npm run dev &
FRONTEND_PID=$!

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID