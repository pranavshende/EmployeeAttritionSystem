import React from 'react';
import { Sparkles, FileText, CheckCircle, TrendingDown, ArrowRight } from 'lucide-react';

export default function AiInsightsBanner({ datasetInfo = {}, aiSummary = '' }) {
  if (!aiSummary && !datasetInfo.is_custom) return null;

  const summaryText = aiSummary || datasetInfo.ai_summary || '';
  const datasetName = datasetInfo.dataset_name || 'Active Dataset';
  const total = (datasetInfo.total_employees || 0).toLocaleString();
  const rate = datasetInfo.attrition_rate || 0;

  return (
    <div
      style={{
        background: '#ffffff',
        border: '1px solid var(--primary-300)',
        borderRadius: 'var(--radius-lg)',
        padding: '18px 22px',
        marginBottom: 'var(--space-xl)',
        boxShadow: '0 4px 20px -2px rgba(16, 185, 129, 0.1)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '4px',
          background: 'var(--gradient-primary)',
        }}
      />

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          marginBottom: '10px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '50%',
              background: 'var(--primary-100)',
              color: 'var(--primary-700)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Sparkles size={16} />
          </div>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 800, color: 'var(--text-main)' }}>
            AI Dataset Intelligence <span style={{ fontWeight: 500, fontSize: '0.8rem', color: 'var(--primary-700)' }}>• Generated on the spot by Gemini</span>
          </h3>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              padding: '3px 10px',
              borderRadius: 'var(--radius-full)',
              background: 'var(--primary-50)',
              border: '1px solid var(--primary-200)',
              fontSize: '0.72rem',
              fontWeight: 700,
              color: 'var(--primary-800)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <FileText size={12} />
            <span>{datasetName}</span>
          </span>
          <span
            style={{
              padding: '3px 10px',
              borderRadius: 'var(--radius-full)',
              background: 'var(--bg-page)',
              border: '1px solid var(--border-subtle)',
              fontSize: '0.72rem',
              fontWeight: 700,
              color: 'var(--text-secondary)',
            }}
          >
            {total} Records • {rate}% Flight Risk
          </span>
          {datasetInfo.is_custom && (
            <span
              style={{
                padding: '3px 10px',
                borderRadius: 'var(--radius-full)',
                background: 'var(--gradient-primary)',
                color: '#ffffff',
                fontSize: '0.7rem',
                fontWeight: 700,
              }}
            >
              Active Custom Dataset
            </span>
          )}
        </div>
      </div>

      <div
        style={{
          fontSize: '0.85rem',
          color: 'var(--text-secondary)',
          lineHeight: 1.6,
          background: 'var(--primary-50)',
          borderRadius: 'var(--radius-md)',
          padding: '12px 16px',
          border: '1px solid var(--primary-200)',
          whiteSpace: 'pre-line',
        }}
      >
        {summaryText}
      </div>
    </div>
  );
}
