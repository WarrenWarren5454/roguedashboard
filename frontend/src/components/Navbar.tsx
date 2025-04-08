import React from 'react';
import { AppBar, Toolbar, Typography, Box, Tabs, Tab } from '@mui/material';

interface NavbarProps {
  currentPage: string;
  onPageChange: (page: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentPage, onPageChange }) => {
  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 0, mr: 4 }}>
          Rogue Dashboard
        </Typography>
        <Box>
          <Tabs 
            value={currentPage} 
            onChange={(_, value) => onPageChange(value)}
            textColor="inherit"
            indicatorColor="secondary"
          >
            <Tab value="credentials" label="Credentials" />
            <Tab value="connections" label="Current Connections" />
          </Tabs>
        </Box>
      </Toolbar>
    </AppBar>
  );
}; 