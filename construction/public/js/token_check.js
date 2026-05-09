(function() {
  const style = getComputedStyle(document.documentElement);
  const mode = document.documentElement.dataset.theme || 'unknown';

  const EXPECTED = {
    dark: {
      '--bg':             '#0b1020',
      '--bg-2':           '#111827',
      '--surface':        '#1e293b',
      '--surface-hover':  '#334155',
      '--text':           '#f8fafc',
      '--text-2':         '#94a3b8',
      '--text-3':         '#64748b',
      '--border':         'rgba(148, 163, 184, 0.18)',
      '--primary':        '#2563eb',
      '--primary-hover':  '#1d4ed8',
      '--accent':         '#f59e0b',
      '--danger':         '#dc2626',
      '--success':        '#16a34a',
      '--radius-sm':      '6px',
      '--radius':         '10px',
      '--radius-lg':      '16px',
      '--radius-xl':      '24px',
      '--radius-full':    '9999px'
    },
    light: {
      '--bg':             '#f8fafc',
      '--bg-2':           '#f1f5f9',
      '--surface':        '#ffffff',
      '--surface-hover':  '#f1f5f9',
      '--text':           '#0f172a',
      '--text-2':         '#475569',
      '--text-3':         '#94a3b8',
      '--border':         'rgba(15, 23, 42, 0.1)',
      '--primary':        '#2563eb',
      '--primary-hover':  '#1d4ed8',
      '--accent':         '#f59e0b',
      '--danger':         '#dc2626',
      '--success':        '#16a34a',
      '--radius-sm':      '6px',
      '--radius':         '10px',
      '--radius-lg':      '16px',
      '--radius-xl':      '24px',
      '--radius-full':    '9999px'
    }
  };

  const expected = EXPECTED[mode];
  if (!expected) {
    console.error('❌ Cannot read theme mode. Is html[data-theme] set?');
    console.log('Current value:', document.documentElement.dataset.theme);
    return;
  }

  let passed = 0, failed = 0;
  const results = [];

  for (const [token, expectedVal] of Object.entries(expected)) {
    const actual = style.getPropertyValue(token).trim();
    const ok = actual === expectedVal;
    if (ok) passed++; else failed++;
    results.push({
      token,
      expected: expectedVal,
      actual: actual || '(empty — token not resolving)',
      status: ok ? '✅ PASS' : '❌ FAIL'
    });
  }

  console.log('');
  console.log('══════════════════════════════════');
  console.log('  CONSTRUCTION THEME TOKEN CHECK  ');
  console.log('══════════════════════════════════');
  console.log('Mode detected:', mode.toUpperCase());
  console.log('');
  console.table(results);
  console.log('');
  console.log('SUMMARY:', passed + ' passed,', failed + ' failed out of', passed + failed, 'tokens');
  if (failed === 0) {
    console.log('🎉 ALL TOKENS RESOLVED CORRECTLY');
  } else {
    console.log('⚠️  FAILED TOKENS NEED FIXING BEFORE NEXT PHASE');
  }
  console.log('══════════════════════════════════');

  return { mode, passed, failed, results };
})();
