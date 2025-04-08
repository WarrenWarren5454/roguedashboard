import React from 'react';
import { CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import { Dashboard } from './components/Dashboard';

const theme = createTheme({
  palette: {
    primary: {
      main: '#c8102e', // UH Red
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Dashboard />
    </ThemeProvider>
  );
}

export default App;
