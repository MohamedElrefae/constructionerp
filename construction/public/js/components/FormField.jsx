/**
 * FormField Component
 * Renders individual form fields based on type
 */

const FormField = (props) => {
  const {
    field,
    value,
    error,
    disabled,
    fullWidth,
    onChange,
    helpText,
    isAutoFilled,
    dependencyMessage
  } = props;

  const [searchResults, setSearchResults] = React.useState([]);
  const [showDropdown, setShowDropdown] = React.useState(false);
  const [loading, setLoading] = React.useState(false);

  // Handle input change
  const handleChange = (e) => {
    const val = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    onChange(val);
  };

  // Handle searchable select
  const handleSearch = async (searchText) => {
    if (!field.link_doctype || searchText.length < 2) {
      setSearchResults([]);
      return;
    }

    setLoading(true);
    try {
      const result = await frappe.call({
        method: 'construction.api.modern_form_api.search_link',
        args: {
          doctype: field.link_doctype,
          txt: searchText
        }
      });

      if (result.message) {
        setSearchResults(result.message.results || []);
        setShowDropdown(true);
      }
    } catch (e) {
      console.error('Search error:', e);
    } finally {
      setLoading(false);
    }
  };

  // Render field based on type
  const renderInput = () => {
    switch (field.type) {
      case 'text':
        return (
          <input
            type="text"
            className={`modern-input ${error ? 'modern-input--error' : ''}`}
            value={value || ''}
            placeholder={field.placeholder}
            disabled={disabled}
            onChange={handleChange}
            autoComplete={field.autoComplete}
          />
        );

      case 'email':
        return (
          <input
            type="email"
            className={`modern-input ${error ? 'modern-input--error' : ''}`}
            value={value || ''}
            placeholder={field.placeholder}
            disabled={disabled}
            onChange={handleChange}
          />
        );

      case 'password':
        return (
          <input
            type="password"
            className={`modern-input ${error ? 'modern-input--error' : ''}`}
            value={value || ''}
            placeholder={field.placeholder}
            disabled={disabled}
            onChange={handleChange}
          />
        );

      case 'number':
        return (
          <input
            type="number"
            className={`modern-input ${error ? 'modern-input--error' : ''}`}
            value={value || ''}
            placeholder={field.placeholder}
            disabled={disabled}
            onChange={handleChange}
            min={field.min}
            max={field.max}
            step={field.step}
          />
        );

      case 'tel':
        return (
          <input
            type="tel"
            className={`modern-input ${error ? 'modern-input--error' : ''}`}
            value={value || ''}
            placeholder={field.placeholder}
            disabled={disabled}
            onChange={handleChange}
          />
        );

      case 'url':
        return (
          <input
            type="url"
            className={`modern-input ${error ? 'modern-input--error' : ''}`}
            value={value || ''}
            placeholder={field.placeholder}
            disabled={disabled}
            onChange={handleChange}
          />
        );

      case 'select':
        return (
          <select
            className={`modern-input modern-select ${error ? 'modern-input--error' : ''}`}
            value={value || ''}
            disabled={disabled}
            onChange={handleChange}
          >
            <option value="">{__('Select...')}</option>
            {field.options?.map(opt => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        );

      case 'searchable-select':
        return (
          <div className="modern-searchable-select">
            <input
              type="text"
              className={`modern-searchable-select__input ${error ? 'modern-input--error' : ''}`}
              value={value || ''}
              placeholder={field.placeholder}
              disabled={disabled}
              onChange={(e) => {
                handleChange(e);
                handleSearch(e.target.value);
              }}
              onFocus={() => value && handleSearch(value)}
            />
            {loading && <span className="modern-searchable-select__loading">...</span>}
            {showDropdown && searchResults.length > 0 && (
              <div className="modern-searchable-select__dropdown">
                {searchResults.map(result => (
                  <div
                    key={result.value}
                    className={`modern-searchable-select__option ${value === result.value ? 'modern-searchable-select__option--selected' : ''}`}
                    onClick={() => {
                      onChange(result.value);
                      setShowDropdown(false);
                    }}
                  >
                    {result.label}
                  </div>
                ))}
              </div>
            )}
          </div>
        );

      case 'checkbox':
        return (
          <label className="modern-checkbox-wrapper">
            <input
              type="checkbox"
              className="modern-checkbox"
              checked={value || false}
              disabled={disabled}
              onChange={handleChange}
            />
            <span>{field.label}</span>
          </label>
        );

      case 'textarea':
        return (
          <textarea
            className={`modern-input modern-textarea ${error ? 'modern-input--error' : ''}`}
            value={value || ''}
            placeholder={field.placeholder}
            disabled={disabled}
            onChange={handleChange}
            rows={field.rows || 4}
          />
        );

      case 'date':
        return (
          <input
            type="date"
            className={`modern-input modern-date-input ${error ? 'modern-input--error' : ''}`}
            value={value || ''}
            disabled={disabled}
            onChange={handleChange}
          />
        );

      case 'datetime':
        return (
          <input
            type="datetime-local"
            className={`modern-input modern-date-input ${error ? 'modern-input--error' : ''}`}
            value={value || ''}
            disabled={disabled}
            onChange={handleChange}
          />
        );

      default:
        return (
          <input
            type="text"
            className={`modern-input ${error ? 'modern-input--error' : ''}`}
            value={value || ''}
            placeholder={field.placeholder}
            disabled={disabled}
            onChange={handleChange}
          />
        );
    }
  };

  return (
    <div className={`modern-form-field ${fullWidth ? 'modern-form-field--full-width' : ''}`}>
      {field.type !== 'checkbox' && (
        <label className={`modern-form-field__label ${field.required ? 'modern-form-field__label--required' : ''}`}>
          {field.label}
          {helpText && (
            <span
              className="modern-tooltip modern-help-icon"
              data-tooltip={helpText}
            >
              ?
            </span>
          )}
          {isAutoFilled && (
            <span className="modern-form-field__autofill">
              <i className="fa fa-magic"></i>
              {__('Auto-filled')}
            </span>
          )}
        </label>
      )}

      <div className="modern-form-field__input-wrapper">
        {renderInput()}
      </div>

      {dependencyMessage && (
        <div className="modern-form-field__dependency">
          <i className="fa fa-lock"></i> {dependencyMessage}
        </div>
      )}

      {error && (
        <div className="modern-form-field__error">
          <i className="fa fa-exclamation-circle"></i>
          {error}
        </div>
      )}
    </div>
  );
};

// Export for global access
window.FormField = FormField;
