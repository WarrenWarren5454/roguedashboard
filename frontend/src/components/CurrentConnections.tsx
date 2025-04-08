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

interface Connection {
  mac_address: string;
  ip_address: string;
  hostname: string;
  connected_since: string;
}

export const CurrentConnections: React.FC = () => {
  const [connections, setConnections] = useState<Connection[]>([]);

  useEffect(() => {
    const fetchConnections = async () => {
      try {
        const response = await fetch('/api/connections');
        const data = await response.json();
        setConnections(data);
      } catch (error) {
        console.error('Failed to fetch connections:', error);
      }
    };

    fetchConnections();
    const interval = setInterval(fetchConnections, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Box sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Current Connections
      </Typography>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow sx={{ bgcolor: '#c8102e' }}>
              <TableCell sx={{ color: 'white' }}>MAC Address</TableCell>
              <TableCell sx={{ color: 'white' }}>IP Address</TableCell>
              <TableCell sx={{ color: 'white' }}>Hostname</TableCell>
              <TableCell sx={{ color: 'white' }}>Connected Since</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {connections.map((conn, index) => (
              <TableRow key={index} sx={{ '&:nth-of-type(even)': { bgcolor: '#f2f2f2' } }}>
                <TableCell>{conn.mac_address}</TableCell>
                <TableCell>{conn.ip_address}</TableCell>
                <TableCell>{conn.hostname}</TableCell>
                <TableCell>{new Date(conn.connected_since).toLocaleString()}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}; 