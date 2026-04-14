/**
 * UltimateButton Component
 * Button with loading, success, and error states
 * From original app TreeView.css
 */

const UltimateButton = (props) => {
  const {
    children,
    variant = 'primary', // 'primary' | 'secondary' | 'danger' | 'success'
    size = 'md', // 'sm' | 'md' | 'lg'
    loading = false,
    success = false,
    error = false,
    disabled = false,
    onClick,
    type = 'button',
    icon,
    className = ''
  } = props;

  const [showSuccess, setShowSuccess] = React.useState(false);
  const [showError, setShowError] = React.useState(false);

  // Handle success/error state display
  React.useEffect(() => {
    if (success) {
      setShowSuccess(true);
      const timer = setTimeout(() => setShowSuccess(false), 1500);
      return () => clearTimeout(timer);
    }
  }, [success]);

  React.useEffect(() => {
    if (error) {
      setShowError(true);
      const timer = setTimeout(() => setShowError(false), 1500);
      return () => clearTimeout(timer);
    }
  }, [error]);

  const handleClick = async (e) => {
    if (loading || disabled || showSuccess || showError) return;
    
    if (onClick) {
      await onClick(e);
    }
  };

  const getButtonClasses = () => {
    const classes = ['ultimate-btn'];
    
    // Variant
    classes.push(`ultimate-btn--${variant}`);
    
    // Size
    if (size === 'sm') classes.push('ultimate-btn--small');
    if (size === 'lg') classes.push('ultimate-btn--large');
    
    // States
    if (loading) classes.push('ultimate-btn--loading');
    if (showSuccess) classes.push('ultimate-btn--success-state');
    if (showError) classes.push('ultimate-btn--error-state');
    if (disabled) classes.push('ultimate-btn--disabled');
    
    // Custom class
    if (className) classes.push(className);
    
    return classes.filter(Boolean).join(' ');
  };

  const renderContent = () => {
    if (loading) {
      return (
        <>
          <span style={{ visibility: 'hidden' }}>{children}</span>
        </>
      );
    }

    if (showSuccess) {
      return (
        <>
          <i className="fa fa-check" style={{ marginRight: '6px' }}></i>
          {__('Success')}
        </>
      );
    }

    if (showError) {
      return (
        <>
          <i className="fa fa-times" style={{ marginRight: '6px' }}></i>
          {__('Error')}
        </>
      );
    }

    return (
      <>
        {icon && (
          <i className={`fa fa-${icon}`} style={{ marginRight: children ? '6px' : '0' }}></i>
        )}
        {children}
      </>
    );
  };

  return (
    <button
      type={type}
      className={getButtonClasses()}
      onClick={handleClick}
      disabled={disabled || loading}
    >
      {renderContent()}
    </button>
  );
};

// Export for global access
window.UltimateButton = UltimateButton;
