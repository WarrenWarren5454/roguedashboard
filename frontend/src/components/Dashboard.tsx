import React, { useEffect, useState } from 'react';
import { Container, Typography, Box } from '@mui/material';
import { CredentialsTable } from './CredentialsTable';
import { Credential } from '../types/types';

export const Dashboard: React.FC = () => {
  const [credentials, setCredentials] = useState<Credential[]>([]);

  const fetchCredentials = async () => {
    try {
      const response = await fetch('/api/creds');
      const data = await response.json();
      setCredentials(data);
    } catch (error) {
      console.error('Failed to fetch credentials:', error);
    }
  };

  useEffect(() => {
    fetchCredentials();
    const interval = setInterval(fetchCredentials, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Captured Credentials
        </Typography>
        <CredentialsTable credentials={credentials} />
      </Box>
    </Container>
  );
}; 