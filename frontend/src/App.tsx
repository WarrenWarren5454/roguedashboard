import React, { useState } from 'react';
import { CssBaseline, ThemeProvider, createTheme, Container } from '@mui/material';
import { Navbar } from './components/Navbar';
import { Credentials } from './components/Credentials';
import { CurrentConnections } from './components/CurrentConnections';

const theme = createTheme({
  palette: {
    primary: {
      main: '#c8102e', // UH Red
    },
    secondary: {
      main: '#ffffff', // White for the tab indicator
    },
  },
});

function App() {
  const [currentPage, setCurrentPage] = useState('credentials');

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Navbar currentPage={currentPage} onPageChange={setCurrentPage} />
      <Container maxWidth="xl">
        {currentPage === 'credentials' ? <Credentials /> : <CurrentConnections />}
      </Container>
    </ThemeProvider>
  );
}

export default App;
