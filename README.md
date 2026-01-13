# draw_flags
Draw a flag, have it recognized

## Quickstart


### Frontend
```bash
cd frontend/
npm install
npm run build
npm run dev
```

The frontend will be available at `http://localhost:5173` (or `http://<your-ip>:5173` for network access)


### Backend
```bash
./scripts/setup-env.sh deploy
./run_backend.sh
```

Note: If you encounter Python version compatibility issues, the project requires Python 3.10-3.13. You can install and pin a compatible version:
```bash
uv python install 3.13
uv python pin 3.13
```
