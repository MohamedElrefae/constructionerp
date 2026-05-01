/**
 * FormLayoutControls Component
 * Controls for form layout customization:
 * - Column count (1/2/3)
 * - Field visibility
 * - Field ordering (drag-drop)
 * - Full-width field toggles
 */

const FormLayoutControls = (props) => {
  const { fields, layout, onChange } = props;

  const [activeTab, setActiveTab] = React.useState('columns'); // 'columns' | 'fields' | 'arrange'
  const [draggedItem, setDraggedItem] = React.useState(null);

  // Handle column count change
  const handleColumnChange = (count) => {
    onChange({
      ...layout,
      columnCount: count
    });
  };

  // Handle field visibility toggle
  const handleVisibilityToggle = (fieldId) => {
    const isVisible = layout.visibleFields.includes(fieldId);
    const newVisibleFields = isVisible
      ? layout.visibleFields.filter(id => id !== fieldId)
      : [...layout.visibleFields, fieldId];

    onChange({
      ...layout,
      visibleFields: newVisibleFields
    });
  };

  // Handle full-width toggle
  const handleFullWidthToggle = (fieldId) => {
    const isFullWidth = layout.fullWidthFields.includes(fieldId);
    const newFullWidthFields = isFullWidth
      ? layout.fullWidthFields.filter(id => id !== fieldId)
      : [...layout.fullWidthFields, fieldId];

    onChange({
      ...layout,
      fullWidthFields: newFullWidthFields
    });
  };

  // Handle drag start
  const handleDragStart = (fieldId) => {
    setDraggedItem(fieldId);
  };

  // Handle drag over
  const handleDragOver = (e, targetFieldId) => {
    e.preventDefault();
    if (!draggedItem || draggedItem === targetFieldId) return;

    const newOrder = [...layout.fieldOrder];
    const draggedIndex = newOrder.indexOf(draggedItem);
    const targetIndex = newOrder.indexOf(targetFieldId);

    newOrder.splice(draggedIndex, 1);
    newOrder.splice(targetIndex, 0, draggedItem);

    onChange({
      ...layout,
      fieldOrder: newOrder
    });
  };

  // Handle drag end
  const handleDragEnd = () => {
    setDraggedItem(null);
  };

  // Move field up/down
  const moveField = (fieldId, direction) => {
    const newOrder = [...layout.fieldOrder];
    const index = newOrder.indexOf(fieldId);

    if (direction === 'up' && index > 0) {
      [newOrder[index], newOrder[index - 1]] = [newOrder[index - 1], newOrder[index]];
    } else if (direction === 'down' && index < newOrder.length - 1) {
      [newOrder[index], newOrder[index + 1]] = [newOrder[index + 1], newOrder[index]];
    }

    onChange({
      ...layout,
      fieldOrder: newOrder
    });
  };

  // Reset to default
  const handleReset = () => {
    onChange({
      columnCount: 2,
      fieldOrder: fields.map(f => f.id),
      fullWidthFields: [],
      visibleFields: fields.map(f => f.id)
    });
  };

  // Save/remember layout
  const handleRemember = () => {
    frappe.show_alert({
      message: __('Layout preferences saved'),
      indicator: 'green'
    });
  };

  // Render columns tab
  const renderColumnsTab = () => (
    <div className="layout-controls__content">
      <p style={{ marginBottom: '16px', color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>
        {__('Choose how many columns to display:')}
      </p>

      <div className="layout-preview">
        {[1, 2, 3].map(colCount => (
          <div
            key={colCount}
            className={`layout-preview__option ${layout.columnCount === colCount ? 'layout-preview__option--active' : ''}`}
            onClick={() => handleColumnChange(colCount)}
          >
            <div className={`layout-preview__visual layout-preview__visual--${colCount}-col`}>
              {Array.from({ length: colCount * 2 }).map((_, i) => (
                <div key={i} className="layout-preview__block"></div>
              ))}
            </div>
            <div className="layout-preview__label">
              {colCount} {colCount === 1 ? __('Column') : __('Columns')}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  // Render fields tab
  const renderFieldsTab = () => (
    <div className="layout-controls__content">
      <ul className="field-visibility-list">
        {fields.map(field => {
          const isVisible = layout.visibleFields.includes(field.id);
          const isFullWidth = layout.fullWidthFields.includes(field.id);

          return (
            <li key={field.id} className="field-visibility-item">
              <div className="field-visibility-item__info">
                <span className="field-visibility-item__icon">
                  <i className="fa fa-arrows"></i>
                </span>
                <span className="field-visibility-item__label">{field.label}</span>
              </div>

              <div className="field-visibility-item__toggle">
                <label className="field-visibility-item__full-width">
                  <input
                    type="checkbox"
                    checked={isFullWidth}
                    onChange={() => handleFullWidthToggle(field.id)}
                  />
                  {__('Full width')}
                </label>

                <label className="modern-checkbox-wrapper" style={{ margin: 0 }}>
                  <input
                    type="checkbox"
                    className="modern-checkbox"
                    checked={isVisible}
                    onChange={() => handleVisibilityToggle(field.id)}
                  />
                  <span style={{ fontSize: 'var(--font-size-sm)' }}>{__('Show')}</span>
                </label>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );

  // Render arrange tab
  const renderArrangeTab = () => (
    <div className="layout-controls__content">
      <p style={{ marginBottom: '16px', color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>
        {__('Drag and drop to reorder fields:')}
      </p>

      <ul className="field-order-list">
        {layout.fieldOrder.map((fieldId, index) => {
          const field = fields.find(f => f.id === fieldId);
          if (!field) return null;

          return (
            <li
              key={field.id}
              className={`field-order-item ${draggedItem === field.id ? 'field-order-item--dragging' : ''}`}
              draggable
              onDragStart={() => handleDragStart(field.id)}
              onDragOver={(e) => handleDragOver(e, field.id)}
              onDragEnd={handleDragEnd}
            >
              <span className="field-order-item__handle">
                <i className="fa fa-grip-vertical"></i>
              </span>
              <span className="field-order-item__label">{field.label}</span>
              <div className="field-order-item__actions">
                <button
                  className="field-order-item__btn field-order-item__btn--up"
                  onClick={() => moveField(field.id, 'up')}
                  disabled={index === 0}
                >
                  <i className="fa fa-chevron-up"></i>
                </button>
                <button
                  className="field-order-item__btn field-order-item__btn--down"
                  onClick={() => moveField(field.id, 'down')}
                  disabled={index === layout.fieldOrder.length - 1}
                >
                  <i className="fa fa-chevron-down"></i>
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );

  return (
    <div className="layout-controls">
      <div className="layout-controls__header">
        <span className="layout-controls__title">
          <i className="fa fa-th-large"></i> {__('Layout Settings')}
        </span>
      </div>

      <div className="layout-controls__tabs">
        <button
          className={`layout-controls__tab ${activeTab === 'columns' ? 'layout-controls__tab--active' : ''}`}
          onClick={() => setActiveTab('columns')}
        >
          {__('Columns')}
        </button>
        <button
          className={`layout-controls__tab ${activeTab === 'fields' ? 'layout-controls__tab--active' : ''}`}
          onClick={() => setActiveTab('fields')}
        >
          {__('Fields')}
        </button>
        <button
          className={`layout-controls__tab ${activeTab === 'arrange' ? 'layout-controls__tab--active' : ''}`}
          onClick={() => setActiveTab('arrange')}
        >
          {__('Arrange')}
        </button>
      </div>

      {activeTab === 'columns' && renderColumnsTab()}
      {activeTab === 'fields' && renderFieldsTab()}
      {activeTab === 'arrange' && renderArrangeTab()}

      <div className="layout-controls__footer">
        <button
          type="button"
          className="layout-btn layout-btn--danger"
          onClick={handleReset}
        >
          <i className="fa fa-undo"></i> {__('Reset')}
        </button>
        <button
          type="button"
          className="layout-btn"
          onClick={handleRemember}
        >
          <i className="fa fa-bookmark"></i> {__('Remember')}
        </button>
        <button
          type="button"
          className="layout-btn layout-btn--primary"
          onClick={() => onChange(layout)}
        >
          <i className="fa fa-save"></i> {__('Save')}
        </button>
      </div>
    </div>
  );
};

// Export for global access
window.FormLayoutControls = FormLayoutControls;
