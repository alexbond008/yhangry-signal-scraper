import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Play, Server, CheckCircle2, AlertCircle, ExternalLink, Mail } from 'lucide-react';
import './index.css';

interface Partner {
  company_name: string;
  domain: string;
  source_url: string;
  location_searched: string;
  snippet: string;
  estimated_property_count?: number;
  luxury_keywords_found: string[];
  luxury_keyword_count: number;
  high_adr_signals: boolean;
  concierge_mentioned: boolean;
  pms_detected: string[];
  channel_managers: string[];
  contact_email?: string;
  companies_house_verified: boolean;
  company_status?: string;
  sic_codes: string[];
  director_name?: string;
  incorporation_year?: number;
  is_property_manager: boolean;
  luxury_tier: string;
  groq_extraction_success: boolean;
  data_sources: string[];
  enrichment_success: boolean;
}

export default function App() {
  const [location, setLocation] = useState('London');
  const [limit, setLimit] = useState(10);
  const [isScraping, setIsScraping] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [results, setResults] = useState<Partner[]>([]);
  const terminalRef = useRef<HTMLDivElement>(null);

  // Auto-scroll terminal
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  const handleScrape = async () => {
    if (!location) return;
    
    setIsScraping(true);
    setLogs([]);
    setResults([]);

    try {
      const response = await fetch(`/api/scrape?location=${encodeURIComponent(location)}&limit=${limit}`);
      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.log) {
                setLogs(prev => [...prev, data.log]);
              }
              if (data.complete) {
                setResults(data.results || []);
                setIsScraping(false);
              }
            } catch (e) {
              console.error("Error parsing stream data", e);
            }
          }
        }
      }
    } catch (error) {
      console.error(error);
      setLogs(prev => [...prev, "ERROR: Pipeline connection failed."]);
      setIsScraping(false);
    }
  };

  return (
    <div className="app-container">
      {/* Header section */}
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1>Signal <span className="gradient-text-gold">Engine</span></h1>
        <p className="subtitle">Discover, verify, and enrich potential yhangry partners with AI.</p>
      </motion.div>

      {/* Control Panel */}
      <motion.div 
        className="glass-panel"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        <div className="search-container">
          <Search size={20} color="var(--text-muted)" />
          <input 
            type="text" 
            className="search-input" 
            placeholder="Target location (e.g. London, Ibiza, Paris)" 
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            disabled={isScraping}
          />
          <input 
            type="number" 
            className="number-input" 
            min="1" 
            max="100" 
            value={limit}
            onChange={(e) => setLimit(parseInt(e.target.value) || 5)}
            disabled={isScraping}
          />
          <button 
            className={`primary-button ${isScraping ? 'processing' : ''}`}
            onClick={handleScrape}
            disabled={isScraping || !location}
          >
            {isScraping ? <Server className="animate-spin" size={18} /> : <Play size={18} />}
            {isScraping ? 'Enriching...' : 'Run Pipeline'}
          </button>
        </div>
      </motion.div>

      {/* Terminal Window */}
      <AnimatePresence>
        {(isScraping || logs.length > 0) && (
          <motion.div 
            className="terminal-window glass-panel"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{ padding: 0 }}
          >
            <div className="terminal-header">
              <div className="terminal-dot dot-red"></div>
              <div className="terminal-dot dot-yellow"></div>
              <div className="terminal-dot dot-green"></div>
              <span style={{ marginLeft: '1rem', color: '#666', fontSize: '0.8rem' }}>pipeline-execution.log</span>
            </div>
            <div className="terminal-body" ref={terminalRef}>
              {logs.map((log, index) => (
                <div key={index} className="terminal-line">
                  <span style={{ color: '#00ff00', marginRight: '8px' }}>&gt;</span>
                  {log}
                </div>
              ))}
              {isScraping && (
                <motion.div 
                  initial={{ opacity: 0 }} 
                  animate={{ opacity: 1 }} 
                  transition={{ repeat: Infinity, duration: 0.8 }}
                  className="terminal-line"
                >
                  <span style={{ color: '#00ff00' }}>_</span>
                </motion.div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Results Section */}
      <AnimatePresence>
        {results.length > 0 && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <h2 style={{ marginBottom: '1rem', fontSize: '1.5rem' }}>
              Enriched Partners ({results.filter(r => r.enrichment_success).length} High Signal)
            </h2>
            
            <div className="stats-overview">
              <div className="stat-box">
                <div className="stat-box-value">{results.length}</div>
                <div className="stat-box-label">Discovered</div>
              </div>
              <div className="stat-box" style={{ borderColor: 'rgba(212, 175, 55, 0.3)' }}>
                <div className="stat-box-value" style={{ color: '#d4af37' }}>
                  {results.filter(r => r.luxury_tier === 'luxury' || r.luxury_tier === 'ultra').length}
                </div>
                <div className="stat-box-label">Luxury Tier</div>
              </div>
              <div className="stat-box" style={{ borderColor: 'rgba(16, 185, 129, 0.3)' }}>
                <div className="stat-box-value" style={{ color: '#10b981' }}>
                  {results.filter(r => r.companies_house_verified).length}
                </div>
                <div className="stat-box-label">Verified (CH)</div>
              </div>
            </div>

            <div className="results-grid">
              {results.map((partner, idx) => (
                <motion.div 
                  key={idx}
                  className="glass-panel partner-card"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: idx * 0.1 }}
                >
                  <div className="partner-header">
                    <div>
                      <h3 className="partner-name">{partner.company_name}</h3>
                      <a href={partner.source_url} target="_blank" rel="noreferrer" className="partner-domain" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        {partner.domain} <ExternalLink size={12} />
                      </a>
                    </div>
                    {partner.companies_house_verified ? (
                      <span className="verification-badge verified" title="Verified on Companies House">
                        <CheckCircle2 size={14} />
                        <span className="verification-text">Verified</span>
                      </span>
                    ) : (
                      <span className="verification-badge unverified" title="Unverified/Not UK Registered">
                        <AlertCircle size={14} />
                        <span className="verification-text">Unverified</span>
                      </span>
                    )}
                  </div>

                  <p className="company-snippet">"{partner.snippet}"</p>

                  <div className="tags-container">
                    {partner.luxury_tier && 
                     partner.luxury_tier.toLowerCase() !== 'null' && 
                     partner.luxury_tier.toLowerCase() !== 'unknown' && (
                      <span className="tag tag-gold">{partner.luxury_tier.toUpperCase()} TIER</span>
                    )}
                    {partner.is_property_manager && (
                      <span className="tag tag-blue">PROPERTY MANAGER</span>
                    )}
                    {partner.concierge_mentioned && (
                      <span className="tag tag-green">CONCIERGE FIT</span>
                    )}
                    {partner.high_adr_signals && (
                      <span className="tag tag-purple">HIGH ADR (£500+)</span>
                    )}
                  </div>

                  <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                    <div className="stat-row">
                      <span className="stat-label">Luxury Keywords</span>
                      <span className="stat-value">{partner.luxury_keyword_count || 0}</span>
                    </div>
                    {partner.channel_managers && partner.channel_managers.length > 0 && (
                      <div className="stat-row">
                        <span className="stat-label">Booking Channels</span>
                        <span className="stat-value">{partner.channel_managers.join(', ')}</span>
                      </div>
                    )}
                    {partner.contact_email && (
                      <div className="stat-row">
                        <span className="stat-label">Contact Email</span>
                        <span className="stat-value" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <Mail size={12} color="var(--accent-blue)" />
                          <a href={`mailto:${partner.contact_email}`} className="email-link">
                            {partner.contact_email}
                          </a>
                        </span>
                      </div>
                    )}
                    {partner.geographic_markets && partner.geographic_markets.length > 0 && (
                      <div className="stat-row">
                        <span className="stat-label">Active Markets</span>
                        <span className="stat-value" title={partner.geographic_markets.join(', ')}>
                          {partner.geographic_markets.slice(0, 3).join(', ')}
                          {partner.geographic_markets.length > 3 && '...'}
                        </span>
                      </div>
                    )}
                  </div>

                  {partner.companies_house_verified && (
                    <div className="companies-house-box">
                      <div className="ch-title">Companies House Records</div>
                      <div className="ch-row">
                        <span>Director:</span>
                        <span className="ch-val" title={partner.director_name}>{partner.director_name || 'Unknown'}</span>
                      </div>
                      <div className="ch-row">
                        <span>Incorporated:</span>
                        <span className="ch-val">
                          {partner.incorporation_year || 'N/A'} ({partner.company_status ? partner.company_status.toUpperCase() : 'ACTIVE'})
                        </span>
                      </div>
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
