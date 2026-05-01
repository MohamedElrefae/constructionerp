/**
 * Sidebar Component
 * Right sidebar navigation matching the old app
 */

const Sidebar = (props) => {
  const {
    sections = [],
    user,
    isOpen = true,
    onClose,
    onNavigate,
    activeItem,
    className = ''
  } = props;

  const [expandedSections, setExpandedSections] = React.useState(
    sections.map((_, i) => i) // All sections expanded by default
  );

  // Toggle section expand/collapse
  const toggleSection = (index) => {
    setExpandedSections(prev =>
      prev.includes(index)
        ? prev.filter(i => i !== index)
        : [...prev, index]
    );
  };

  // Handle navigation
  const handleNavigate = (item) => {
    if (onNavigate) onNavigate(item);
  };

  return (
    <>
      {/* Sidebar */}
      <div className={`modern-sidebar ${isOpen ? '' : 'modern-sidebar--closed'} ${className}`}>
        {/* Header */}
        <div className="modern-sidebar__header">
          <span className="modern-sidebar__title">
            <i className="fa fa-th-large"></i> {__('Menu')}
          </span>
          <div
            className="modern-sidebar__close"
            onClick={onClose}
          >
            <i className="fa fa-times"></i>
          </div>
        </div>

        {/* Content */}
        <div className="modern-sidebar__content">
          {sections.map((section, index) => (
            <div
              key={section.id || index}
              className={[
                'modern-sidebar__section',
                expandedSections.includes(index) ? '' : 'modern-sidebar__section--collapsed'
              ].filter(Boolean).join(' ')}
            >
              {/* Section Header */}
              <div
                className="modern-sidebar__section-header"
                onClick={() => toggleSection(index)}
              >
                <span className="modern-sidebar__section-title">
                  {section.icon && <i className={`fa fa-${section.icon}`} style={{ marginRight: '8px' }}></i>}
                  {section.title}
                </span>
                <span className="modern-sidebar__section-toggle">
                  <i className="fa fa-chevron-down"></i>
                </span>
              </div>

              {/* Section Content */}
              <div className="modern-sidebar__section-content">
                <ul className="modern-sidebar__menu">
                  {section.items.map((item, itemIndex) => (
                    <li key={item.id || itemIndex} className="modern-sidebar__menu-item">
                      <a
                        href={item.href || '#'}
                        className={[
                          'modern-sidebar__menu-link',
                          activeItem === item.id ? 'modern-sidebar__menu-link--active' : ''
                        ].filter(Boolean).join(' ')}
                        onClick={(e) => {
                          e.preventDefault();
                          handleNavigate(item);
                        }}
                      >
                        {item.icon && (
                          <span className="modern-sidebar__menu-icon">
                            <i className={`fa fa-${item.icon}`}></i>
                          </span>
                        )}
                        <span className="modern-sidebar__menu-text">{item.label}</span>
                        {item.badge && (
                          <span className="modern-sidebar__menu-badge">{item.badge}</span>
                        )}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>

        {/* Footer - User Info */}
        {user && (
          <div className="modern-sidebar__footer">
            <div className="modern-sidebar__user-info">
              <div className="modern-sidebar__user-avatar">
                {user.avatar ? (
                  <img src={user.avatar} alt={user.name} style={{ width: '100%', height: '100%', borderRadius: '50%' }} />
                ) : (
                  user.name ? user.name.charAt(0).toUpperCase() : 'U'
                )}
              </div>
              <div className="modern-sidebar__user-details">
                <div className="modern-sidebar__user-name">{user.name}</div>
                <div className="modern-sidebar__user-role">{user.role}</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Toggle Button (when sidebar is closed) */}
      {!isOpen && (
        <div
          className="modern-sidebar-toggle"
          onClick={() => onClose && onClose()}
        >
          <span className="modern-sidebar-toggle__icon">
            <i className="fa fa-chevron-left"></i>
          </span>
        </div>
      )}

      {/* Overlay (for mobile) */}
      {isOpen && (
        <div
          className="modern-sidebar-overlay modern-sidebar-overlay--visible"
          onClick={onClose}
        />
      )}
    </>
  );
};

// Export for global access
window.Sidebar = Sidebar;
