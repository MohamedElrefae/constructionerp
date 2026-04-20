/**
 * TreeView Component
 * Hierarchical tree display with columns
 * Supports: كود, اسم الحساب, نوع الحساب, المستوى, الإجراءات
 */

const TreeView = (props) => {
  const {
    data = [],
    columns = ['code', 'name', 'type', 'level', 'actions'],
    onEdit,
    onAdd,
    onDelete,
    onToggleStatus,
    onSelect,
    onToggleExpand,
    expandedNodes = [],
    selectedNode = null,
    className = ''
  } = props;

  const [expanded, setExpanded] = React.useState(expandedNodes);
  const [selected, setSelected] = React.useState(selectedNode);
  const [buttonStates, setButtonStates] = React.useState({});

  // Handle expand/collapse
  const toggleExpand = (nodeId, hasChildren) => {
    if (!hasChildren) return;
    
    const newExpanded = expanded.includes(nodeId)
      ? expanded.filter(id => id !== nodeId)
      : [...expanded, nodeId];
    
    setExpanded(newExpanded);
    if (onToggleExpand) onToggleExpand(nodeId, !expanded.includes(nodeId));
  };

  // Handle node selection
  const handleSelect = (node) => {
    setSelected(node.id);
    if (onSelect) onSelect(node);
  };

  // Handle action with button feedback
  const handleAction = async (action, node, e) => {
    e.stopPropagation();
    
    // Set button loading state
    const buttonKey = `${action}-${node.id}`;
    setButtonStates(prev => ({ ...prev, [buttonKey]: 'loading' }));
    
    try {
      let result;
      switch (action) {
        case 'edit':
          if (onEdit) result = await onEdit(node);
          break;
        case 'add':
          if (onAdd) result = await onAdd(node);
          break;
        case 'toggle':
          if (onToggleStatus) result = await onToggleStatus(node);
          break;
        case 'delete':
          if (confirm(__('Are you sure?'))) {
            if (onDelete) result = await onDelete(node);
          }
          break;
      }
      
      // Show success state briefly
      setButtonStates(prev => ({ ...prev, [buttonKey]: 'success' }));
      setTimeout(() => {
        setButtonStates(prev => {
          const newState = { ...prev };
          delete newState[buttonKey];
          return newState;
        });
      }, 1000);
      
    } catch (error) {
      setButtonStates(prev => ({ ...prev, [buttonKey]: 'error' }));
      setTimeout(() => {
        setButtonStates(prev => {
          const newState = { ...prev };
          delete newState[buttonKey];
          return newState;
        });
      }, 1000);
    }
  };

  // Get button class based on state
  const getButtonClass = (action, nodeId) => {
    const state = buttonStates[`${action}-${nodeId}`];
    const baseClass = 'modern-tree-action-btn';
    
    if (state === 'loading') return `${baseClass} ultimate-btn--loading`;
    if (state === 'success') return `${baseClass} ultimate-btn--success-state`;
    if (state === 'error') return `${baseClass} ultimate-btn--error-state`;
    
    return `${baseClass} modern-tree-action-btn--${action}`;
  };

  // Render tree node
  const renderNode = (node, level = 0) => {
    const isExpanded = expanded.includes(node.id);
    const isSelected = selected === node.id;
    const isInactive = node.status === 'inactive';
    const hasChildren = node.has_children || (node.children && node.children.length > 0);

    return (
      <React.Fragment key={node.id}>
        <div
          className={[
            'modern-tree-node',
            `modern-tree-node--level-${Math.min(level, 6)}`,
            isSelected ? 'modern-tree-node--selected' : '',
            isInactive ? 'modern-tree-node--inactive' : ''
          ].filter(Boolean).join(' ')}
          onClick={() => handleSelect(node)}
        >
          {/* Expander */}
          <div className="modern-tree-node__indent" style={{ width: level * 20 }}></div>
          <div
            className={[
              'modern-tree-node__expander',
              isExpanded ? 'modern-tree-node__expander--expanded' : '',
              !hasChildren ? 'modern-tree-node__expander--placeholder' : ''
            ].filter(Boolean).join(' ')}
            onClick={(e) => {
              e.stopPropagation();
              toggleExpand(node.id, hasChildren);
            }}
          >
            {hasChildren && (
              <i className="fa fa-chevron-right"></i>
            )}
          </div>

          {/* Status Dot */}
          <div className="modern-tree-node__status">
            <span className="modern-tree-node__status-dot"></span>
          </div>

          {/* Columns */}
          {columns.map(col => {
            switch (col) {
              case 'code':
                return (
                  <div key={col} className="modern-tree-node__code">
                    {node.code}
                  </div>
                );
              
              case 'name':
                return (
                  <div key={col} className="modern-tree-node__name">
                    {node.name}
                  </div>
                );
              
              case 'type':
                return (
                  <div key={col} className="modern-tree-node__type">
                    {node.account_type || node.type || '-'}
                  </div>
                );
              
              case 'level':
                return (
                  <div key={col} className="modern-tree-node__level">
                    {node.level}
                  </div>
                );
              
              case 'actions':
                return (
                  <div key={col} className="modern-tree-node__actions">
                    {onEdit && (
                      <button
                        className={getButtonClass('edit', node.id)}
                        onClick={(e) => handleAction('edit', node, e)}
                        title={__('Edit')}
                      >
                        <i className="fa fa-edit"></i>
                        {__('تعديل')}
                      </button>
                    )}
                    
                    {onAdd && (
                      <button
                        className={getButtonClass('add', node.id)}
                        onClick={(e) => handleAction('add', node, e)}
                        title={__('Add Child')}
                      >
                        <i className="fa fa-plus"></i>
                        {__('إضافة فرعي')}
                      </button>
                    )}
                    
                    {onToggleStatus && (
                      <button
                        className={getButtonClass('toggle', node.id)}
                        onClick={(e) => handleAction('toggle', node, e)}
                        title={isInactive ? __('Activate') : __('Deactivate')}
                      >
                        <i className={`fa fa-${isInactive ? 'check' : 'ban'}`}></i>
                        {isInactive ? __('تفعيل') : __('تعطيل')}
                      </button>
                    )}
                    
                    {onDelete && (
                      <button
                        className={getButtonClass('delete', node.id)}
                        onClick={(e) => handleAction('delete', node, e)}
                        title={__('Delete')}
                      >
                        <i className="fa fa-trash"></i>
                        {__('حذف')}
                      </button>
                    )}
                  </div>
                );
              
              default:
                return (
                  <div key={col} className="modern-tree-node__extra">
                    {node[col] || '-'}
                  </div>
                );
            }
          })}
        </div>

        {/* Render children if expanded */}
        {hasChildren && isExpanded && node.children && (
          <div className="modern-tree-children">
            {node.children.map(child => renderNode(child, level + 1))}
          </div>
        )}
      </React.Fragment>
    );
  };

  return (
    <div className={`modern-tree-view ${className}`}>
      {/* Header */}
      <div className="modern-tree-view__header">
        <div className="modern-tree-view__header-cell"></div> {/* Expander placeholder */}
        <div className="modern-tree-view__header-cell"></div> {/* Status placeholder */}
        <div className="modern-tree-view__header-cell"></div> {/* Indent placeholder */}
        {columns.map(col => {
          const headers = {
            code: __('كود'),
            name: __('اسم الحساب'),
            type: __('نوع الحساب'),
            level: __('المستوى'),
            actions: __('الإجراءات')
          };
          return (
            <div key={col} className="modern-tree-view__header-cell">
              {headers[col] || col}
            </div>
          );
        })}
      </div>

      {/* Body */}
      <div className="modern-tree-view__body">
        {data.length === 0 ? (
          <div style={{ 
            padding: '40px', 
            textAlign: 'center', 
            color: 'var(--text-secondary)'
          }}>
            <i className="fa fa-folder-open" style={{ fontSize: '48px', marginBottom: '16px', opacity: 0.5 }}></i>
            <p>{__('No data available')}</p>
          </div>
        ) : (
          data.map(node => renderNode(node))
        )}
      </div>
    </div>
  );
};

// Export for global access
window.TreeView = TreeView;
