/**
 * ExportButtons Component
 * Excel and PDF export buttons with modern styling
 */

const ExportButtons = (props) => {
  const {
    onExportExcel,
    onExportPDF,
    disabled = false,
    loading = false,
    className = ''
  } = props;

  const [activeButton, setActiveButton] = React.useState(null);

  const handleExport = async (type) => {
    if (loading || disabled) return;

    setActiveButton(type);

    try {
      if (type === 'excel' && onExportExcel) {
        await onExportExcel();
      } else if (type === 'pdf' && onExportPDF) {
        await onExportPDF();
      }
    } catch (error) {
      console.error('Export error:', error);
      frappe.show_alert({
        message: __('Export failed'),
        indicator: 'red'
      });
    } finally {
      setActiveButton(null);
    }
  };

  return (
    <div className={`export-buttons-container ${className}`}>
      {/* Excel Export Button */}
      <button
        className={[
          'export-btn',
          'export-btn--excel',
          activeButton === 'excel' ? 'ultimate-btn--loading' : ''
        ].filter(Boolean).join(' ')}
        onClick={() => handleExport('excel')}
        disabled={disabled || loading}
        title={__('Export to Excel')}
      >
        {activeButton === 'excel' ? (
          <i className="fa fa-spinner fa-spin"></i>
        ) : (
          <i className="fa fa-file-excel-o"></i>
        )}
        {__('Excel')}
      </button>

      {/* PDF Export Button */}
      <button
        className={[
          'export-btn',
          'export-btn--pdf',
          activeButton === 'pdf' ? 'ultimate-btn--loading' : ''
        ].filter(Boolean).join(' ')}
        onClick={() => handleExport('pdf')}
        disabled={disabled || loading}
        title={__('Export to PDF')}
      >
        {activeButton === 'pdf' ? (
          <i className="fa fa-spinner fa-spin"></i>
        ) : (
          <i className="fa fa-file-pdf-o"></i>
        )}
        {__('PDF')}
      </button>
    </div>
  );
};

// Export for global access
window.ExportButtons = ExportButtons;
