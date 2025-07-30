import React, { useState } from 'react';
import './App.css';

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [extractedData, setExtractedData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file);
      setPreview(URL.createObjectURL(file));
      setExtractedData(null);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      setPreview(URL.createObjectURL(file));
      setExtractedData(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    
    setLoading(true);
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    try {
      const response = await fetch('http://localhost:5001/api/upload', {
        method: 'POST',
        body: formData,
      });
      
      const data = await response.json();
      setExtractedData(data);
    } catch (error) {
      console.error('Error uploading file:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    if (amount === null || amount === undefined) return 'N/A';
    return new Intl.NumberFormat('th-TH', {
      style: 'currency',
      currency: 'THB',
    }).format(amount);
  };

  return (
    <div className="app-container">
      <header>
        <h1>Demo Slip OCR Extractor</h1>
        <p className="user-info">User : Admin</p>
      </header>
      
      <main>
        <div className="upload-section">
          <h2>Upload Slip Image</h2>
          
          <div 
            className={`upload-area ${dragActive ? 'drag-active' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <input 
              type="file" 
              accept="image/*" 
              id="upload-input"
              onChange={handleFileChange}
              className="file-input"
            />
            
            {!preview ? (
              <div className="upload-prompt">
                <div className="upload-icon">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="48" height="48">
                    <path d="M12 16l4-5h-3V4h-2v7H8z" fill="currentColor"/>
                    <path d="M20 18H4v-7H2v7c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2v-7h-2v7z" fill="currentColor"/>
                  </svg>
                </div>
                <p>Drag & drop your slip image here or</p>
                <label htmlFor="upload-input" className="upload-btn">Browse Files</label>
                <p className="upload-hint">Supports: JPG, PNG, JPEG</p>
              </div>
            ) : (
              <div className="preview-container">
                <img src={preview} alt="Preview" className="preview-image" />
                <div className="preview-actions">
                  <span className="file-name">{selectedFile?.name}</span>
                  <button 
                    className="remove-btn"
                    onClick={() => {
                      setSelectedFile(null);
                      setPreview(null);
                    }}
                  >
                    Change
                  </button>
                </div>
              </div>
            )}
          </div>
          
          <button 
            onClick={handleUpload} 
            disabled={!selectedFile || loading}
            className="upload-button"
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                <span>Processing...</span>
              </>
            ) : 'Extract Data'}
          </button>
        </div>
        
        {extractedData && (
          <div className="results-section">
            <h2>Extracted Data</h2>
            <div className="data-card">
              <div className="data-row">
                <div className="data-label">Bank</div>
                <div className="data-value">{extractedData.bank || 'N/A'}</div>
              </div>
              <div className="data-row">
                <div className="data-label">Recipient</div>
                <div className="data-value">{extractedData.recipient_name || 'N/A'}</div>
              </div>
              <div className="data-row">
                <div className="data-label">Amount</div>
                <div className="data-value amount">{formatCurrency(extractedData.amount)}</div>
              </div>
              <div className="data-row">
                <div className="data-label">Date & Time</div>
                <div className="data-value">
                  {extractedData.transaction_datetime 
                    ? new Date(extractedData.transaction_datetime).toLocaleString() 
                    : 'N/A'}
                </div>
              </div>
              <div className="data-row">
                <div className="data-label">Transaction ID</div>
                <div className="data-value">{extractedData.transaction_id || 'N/A'}</div>
              </div>
            </div>
          </div>
        )}
      </main>
      
      <footer>
        <p>Current Date: {new Date().toLocaleString()}</p>
      </footer>
    </div>
  );
}

export default App;