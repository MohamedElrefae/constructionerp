/**
 * UnifiedCRUDForm Component
 * Hybrid form for Create, Read, Update, Delete operations
 * Bridges Frappe backend with React frontend
 */

const UnifiedCRUDForm = (props) => {
  const {
    config,
    initialData = {},
    mode = 'create', // 'create' | 'edit' | 'view'
    onSubmit,
    onCancel,
    onDelete,
    className = ''
  } = props;

  const [formData, setFormData] = React.useState(initialData);
  const [errors, setErrors] = React.useState({});
  const [loading, setLoading] = React.useState(false);
  const [layout, setLayout] = React.useState({
    columnCount: 2,
    fieldOrder: config.fields.map(f => f.id),
    fullWidthFields: [],
    visibleFields: config.fields.map(f => f.id)
  });

  // Load layout preferences from localStorage
  React.useEffect(() => {
    const savedLayout = localStorage.getItem(`form_layout_${config.doctype}`);
    if (savedLayout) {
      setLayout(JSON.parse(savedLayout));
    }
  }, [config.doctype]);

  // Handle field change
  const handleChange = (fieldId, value) => {
    setFormData(prev => ({
      ...prev,
      [fieldId]: value
    }));

    // Clear error for this field
    if (errors[fieldId]) {
      setErrors(prev => ({
        ...prev,
        [fieldId]: null
      }));
    }

    // Handle dependencies
    handleDependencies(fieldId, value);
  };

  // Handle field dependencies
  const handleDependencies = (changedFieldId, value) => {
    config.fields.forEach(field => {
      if (field.dependsOnAny && field.dependsOnAny.includes(changedFieldId)) {
        // Reset field that depends on this one
        setFormData(prev => ({
          ...prev,
          [field.id]: field.defaultValue || ''
        }));
      }
    });
  };

  // Validate form
  const validateForm = async () => {
    const newErrors = {};

    for (const field of config.fields) {
      // Skip hidden fields
      if (!layout.visibleFields.includes(field.id)) continue;

      // Check conditional logic
      if (field.conditionalLogic && !field.conditionalLogic(formData)) continue;

      const value = formData[field.id];

      // Required validation
      if (field.required && !value) {
        newErrors[field.id] = `${field.label} is required`;
        continue;
      }

      // Custom validation
      if (field.validation && value) {
        const error = field.validation(value);
        if (error) {
          newErrors[field.id] = error;
        }
      }

      // Server-side validation for critical fields
      if (field.serverValidation && value) {
        try {
          const result = await frappe.call({
            method: 'construction.api.modern_form_api.validate_field',
            args: {
              doctype: config.doctype,
              fieldname: field.id,
              value: value,
              context: formData
            }
          });

          if (!result.message.valid) {
            newErrors[field.id] = result.message.errors[0];
          }
        } catch (e) {
          console.error('Validation error:', e);
        }
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle submit
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (mode === 'view') {
      onCancel && onCancel();
      return;
    }

    setLoading(true);

    const isValid = await validateForm();
    if (!isValid) {
      setLoading(false);
      frappe.show_alert({
        message: __('Please fix the errors before submitting'),
        indicator: 'red'
      });
      return;
    }

    try {
      const result = await onSubmit(formData);
      if (result.success) {
        frappe.show_alert({
          message: result.message || __('Saved successfully'),
          indicator: 'green'
        });
      }
    } catch (error) {
      frappe.show_alert({
        message: error.message || __('An error occurred'),
        indicator: 'red'
      });
    } finally {
      setLoading(false);
    }
  };

  // Handle layout change
  const handleLayoutChange = (newLayout) => {
    setLayout(newLayout);
    localStorage.setItem(`form_layout_${config.doctype}`, JSON.stringify(newLayout));
  };

  // Get visible and ordered fields
  const getOrderedFields = () => {
    return layout.fieldOrder
      .map(id => config.fields.find(f => f.id === id))
      .filter(field => field && layout.visibleFields.includes(field.id))
      .filter(field => {
        // Check conditional logic
        if (field.conditionalLogic) {
          return field.conditionalLogic(formData);
        }
        return true;
      });
  };

  // Render field
  const renderField = (field) => {
    const value = formData[field.id];
    const error = errors[field.id];
    const isFullWidth = layout.fullWidthFields.includes(field.id);
    const isDisabled = mode === 'view' || field.disabled ||
      (field.dependsOn && !formData[field.dependsOn]);

    return (
      <FormField
        key={field.id}
        field={field}
        value={value}
        error={error}
        disabled={isDisabled}
        fullWidth={isFullWidth}
        onChange={(val) => handleChange(field.id, val)}
        helpText={field.helpText}
        isAutoFilled={field.autoFill && value && !initialData[field.id]}
        dependencyMessage={field.dependsOn && !formData[field.dependsOn] ?
          field.dependencyErrorMessage || `Requires ${field.dependsOn}` : null}
      />
    );
  };

  const orderedFields = getOrderedFields();
  const gridClass = `modern-form-grid--${layout.columnCount}-col`;

  return (
    <form
      className={`modern-crud-form ${className}`}
      onSubmit={handleSubmit}
    >
      {/* Header */}
      <div className="modern-crud-form__header">
        <h2 className="modern-crud-form__title">
          {mode === 'create' ? `Create ${config.title}` :
           mode === 'edit' ? `Edit ${config.title}` :
           config.title}
        </h2>
        <div className="modern-crud-form__actions">
          {mode !== 'view' && (
            <button
              type="button"
              className="ultimate-btn ultimate-btn--secondary"
              onClick={() => setShowLayoutControls(!showLayoutControls)}
            >
              <i className="fa fa-cog"></i>
            </button>
          )}
        </div>
      </div>

      {/* Layout Controls */}
      {showLayoutControls && mode !== 'view' && (
        <FormLayoutControls
          fields={config.fields}
          layout={layout}
          onChange={handleLayoutChange}
        />
      )}

      {/* Validation Summary */}
      {Object.keys(errors).length > 0 && (
        <div className="modern-validation-summary">
          <div className="modern-validation-summary__title">
            <i className="fa fa-exclamation-circle"></i>
            {__('Please fix the following errors:')}
          </div>
          <ul className="modern-validation-summary__list">
            {Object.entries(errors).map(([fieldId, error]) => (
              <li key={fieldId}>{error}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Form Body */}
      <div className="modern-crud-form__body">
        <div className={`modern-form-grid ${gridClass}`}>
          {orderedFields.map(renderField)}
        </div>
      </div>

      {/* Footer */}
      <div className="modern-crud-form__footer">
        {mode !== 'create' && onDelete && (
          <button
            type="button"
            className="ultimate-btn ultimate-btn--danger"
            onClick={() => {
              if (confirm(__('Are you sure you want to delete this?'))) {
                onDelete(formData.name);
              }
            }}
            disabled={loading}
          >
            {__('Delete')}
          </button>
        )}

        <div style={{ flex: 1 }}></div>

        <button
          type="button"
          className="ultimate-btn ultimate-btn--secondary"
          onClick={onCancel}
          disabled={loading}
        >
          {__('Cancel')}
        </button>

        {mode !== 'view' && (
          <button
            type="submit"
            className={`ultimate-btn ultimate-btn--primary ${loading ? 'ultimate-btn--loading' : ''}`}
            disabled={loading}
          >
            {mode === 'create' ? __('Create') : __('Save')}
          </button>
        )}
      </div>
    </form>
  );
};

// Export for global access
window.UnifiedCRUDForm = UnifiedCRUDForm;
