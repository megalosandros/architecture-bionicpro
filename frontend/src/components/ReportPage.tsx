import React, { useState } from 'react';
import { useKeycloak } from '@react-keycloak/web';

interface Report {
  customer_id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  country_code: string;
  order_id: string;
  order_date: string;
  total_amount: number;
  order_status: string;
  prosthesis_id: string;
  prosthesis_type: string;
  manufacture_date: string;
  delivery_date: string;
  warranty_end_date: string;
  prosthesis_status: string;
  telemetry_events_count: number;
  avg_battery_level: number;
  avg_response_time_ms: number;
  avg_signal_quality: number;
  most_common_movement: string;
  total_errors: number;
  last_telemetry_date: string | null;
  report_generated_at: string;
  data_actual_as_of: string;
}

const ReportPage: React.FC = () => {
  const { keycloak, initialized } = useKeycloak();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reports, setReports] = useState<Report[] | null>(null);

  const loadReport = async () => {
    console.log('=== Load Report clicked ===');
    console.log('Keycloak token:', keycloak?.token ? 'EXISTS' : 'MISSING');
    console.log('API URL:', process.env.REACT_APP_API_URL);
    
    if (!keycloak?.token) {
      setError('Not authenticated');
      console.error('No keycloak token!');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setReports(null);

      const apiUrl = `${process.env.REACT_APP_API_URL}/reports`;
      console.log('Fetching from:', apiUrl);

      const response = await fetch(apiUrl, {
        headers: {
          'Authorization': `Bearer ${keycloak.token}`
        }
      });

      console.log('Response status:', response.status);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Received data:', data);
      console.log('Data is array:', Array.isArray(data));
      console.log('Data length:', data?.length);
      console.log('First item:', data?.[0]);
      
      setReports(data);
      console.log('Reports state updated');
      
    } catch (err) {
      console.error('Error details:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  if (!initialized) {
    return <div>Loading...</div>;
  }

  if (!keycloak.authenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        <button
          onClick={() => keycloak.login()}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Login
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 p-4">
      <div className="w-full max-w-6xl p-8 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold mb-6">Usage Reports</h1>
        
        <button
          onClick={loadReport}
          disabled={loading}
          className={`px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 ${
            loading ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {loading ? 'Loading Report...' : 'Load Report'}
        </button>

        {error && (
          <div className="mt-4 p-4 bg-red-100 text-red-700 rounded">
            {error}
          </div>
        )}

        {reports && reports.length > 0 && (
          <div className="mt-6 overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-green-600 text-white">
                  <th className="border border-gray-300 px-3 py-2 text-left">Customer</th>
                  <th className="border border-gray-300 px-3 py-2 text-left">Contact</th>
                  <th className="border border-gray-300 px-3 py-2 text-left">Order ID</th>
                  <th className="border border-gray-300 px-3 py-2 text-left">Order Date</th>
                  <th className="border border-gray-300 px-3 py-2 text-left">Status</th>
                  <th className="border border-gray-300 px-3 py-2 text-left">Telemetry Events</th>
                  <th className="border border-gray-300 px-3 py-2 text-left">Battery %</th>
                  <th className="border border-gray-300 px-3 py-2 text-left">Response Time (ms)</th>
                  <th className="border border-gray-300 px-3 py-2 text-left">Errors</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((report, index) => (
                  <tr key={index} className={index % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                    <td className="border border-gray-300 px-3 py-2">
                      {report.first_name} {report.last_name}
                      <br />
                      <span className="text-xs text-gray-500">{report.country_code}</span>
                    </td>
                    <td className="border border-gray-300 px-3 py-2 text-xs">
                      {report.email}
                      <br />
                      {report.phone}
                    </td>
                    <td className="border border-gray-300 px-3 py-2">{report.order_id}</td>
                    <td className="border border-gray-300 px-3 py-2">
                      {new Date(report.order_date).toLocaleDateString()}
                    </td>
                    <td className="border border-gray-300 px-3 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        report.order_status === 'completed' ? 'bg-green-200' : 'bg-yellow-200'
                      }`}>
                        {report.order_status}
                      </span>
                    </td>
                    <td className="border border-gray-300 px-3 py-2 text-center">
                      {report.telemetry_events_count}
                    </td>
                    <td className="border border-gray-300 px-3 py-2 text-center">
                      {report.avg_battery_level?.toFixed(1) ?? 'N/A'}
                    </td>
                    <td className="border border-gray-300 px-3 py-2 text-center">
                      {report.avg_response_time_ms?.toFixed(1) ?? 'N/A'}
                    </td>
                    <td className="border border-gray-300 px-3 py-2 text-center">
                      <span className={report.total_errors > 0 ? 'text-red-600 font-bold' : ''}>
                        {report.total_errors}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {reports && reports.length === 0 && (
          <div className="mt-4 p-4 bg-yellow-100 text-yellow-700 rounded">
            No data found
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportPage;