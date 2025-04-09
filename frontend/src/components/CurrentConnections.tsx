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
  Chip,
} from '@mui/material';

interface Connection {
  mac: string;
  ip: string;
  hostname: string;
  connected_since: number;
  rx_mb: number;
  tx_mb: number;
  status: string;
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

  const formatTimestamp = (timestamp: number) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
  };

  return (
    <Box sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Current Connections
      </Typography>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow sx={{ bgcolor: '#c8102e' }}>
              <TableCell sx={{ color: 'white' }}>Status</TableCell>
              <TableCell sx={{ color: 'white' }}>MAC Address</TableCell>
              <TableCell sx={{ color: 'white' }}>IP Address</TableCell>
              <TableCell sx={{ color: 'white' }}>Hostname</TableCell>
              <TableCell sx={{ color: 'white' }}>Connected Since</TableCell>
              <TableCell sx={{ color: 'white' }}>Data Received</TableCell>
              <TableCell sx={{ color: 'white' }}>Data Sent</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {connections.map((conn, index) => (
              <TableRow key={index} sx={{ '&:nth-of-type(even)': { bgcolor: '#f2f2f2' } }}>
                <TableCell>
                  <Chip 
                    label={conn.status} 
                    color={conn.status === 'Connected' ? 'success' : 'default'}
                    size="small"
                  />
                </TableCell>
                <TableCell>{conn.mac}</TableCell>
                <TableCell>{conn.ip}</TableCell>
                <TableCell>{conn.hostname}</TableCell>
                <TableCell>{formatTimestamp(conn.connected_since)}</TableCell>
                <TableCell>{conn.rx_mb ? `${conn.rx_mb.toFixed(2)} MB` : 'N/A'}</TableCell>
                <TableCell>{conn.tx_mb ? `${conn.tx_mb.toFixed(2)} MB` : 'N/A'}</TableCell>
              </TableRow>
            ))}
            {connections.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  No connections found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}; 