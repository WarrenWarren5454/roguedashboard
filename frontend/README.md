# Rogue Dashboard Frontend

This is the React frontend for the Rogue Dashboard application. It provides a modern, responsive interface for viewing captured credentials.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm start
```

The development server will run on http://localhost:3000

## Building for Production

To build the frontend for production:

```bash
npm run build
```

This will create a `build` directory with optimized production files. The Flask backend will automatically serve these files when accessing the `/dashboard` route.

## Features

- Real-time updates every 2 seconds
- Modern Material-UI components
- Responsive design that works on all screen sizes
- TypeScript for better development experience
- UH branding colors and styling
