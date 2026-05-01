/**
 * DraggableResizablePanel Component
 * Draggable, resizable, dockable panel with maximize functionality
 */

const DraggablePanel = (props) => {
  const {
    title,
    children,
    initialPosition = { x: 100, y: 100 },
    initialSize = { width: 600, height: 500 },
    minSize = { width: 400, height: 300 },
    onClose,
    onDock,
    className = ''
  } = props;

  const panelRef = React.useRef(null);

  const [position, setPosition] = React.useState(initialPosition);
  const [size, setSize] = React.useState(initialSize);
  const [isMaximized, setIsMaximized] = React.useState(false);
  const [isDocked, setIsDocked] = React.useState(false);
  const [isDragging, setIsDragging] = React.useState(false);
  const [isResizing, setIsResizing] = React.useState(false);
  const [resizeHandle, setResizeHandle] = React.useState(null);

  const dragStartPos = React.useRef({ x: 0, y: 0 });
  const panelStartPos = React.useRef({ x: 0, y: 0 });
  const resizeStart = React.useRef({ x: 0, y: 0, width: 0, height: 0 });

  // Handle drag start
  const handleDragStart = (e) => {
    if (isMaximized || isDocked) return;

    setIsDragging(true);
    dragStartPos.current = { x: e.clientX, y: e.clientY };
    panelStartPos.current = { ...position };

    // Add global event listeners
    document.addEventListener('mousemove', handleDragMove);
    document.addEventListener('mouseup', handleDragEnd);
  };

  // Handle drag move
  const handleDragMove = React.useCallback((e) => {
    if (!isDragging) return;

    const deltaX = e.clientX - dragStartPos.current.x;
    const deltaY = e.clientY - dragStartPos.current.y;

    setPosition({
      x: panelStartPos.current.x + deltaX,
      y: panelStartPos.current.y + deltaY
    });
  }, [isDragging]);

  // Handle drag end
  const handleDragEnd = React.useCallback(() => {
    setIsDragging(false);
    document.removeEventListener('mousemove', handleDragMove);
    document.removeEventListener('mouseup', handleDragEnd);
  }, [handleDragMove]);

  // Handle resize start
  const handleResizeStart = (e, handle) => {
    e.stopPropagation();
    e.preventDefault();

    if (isMaximized || isDocked) return;

    setIsResizing(true);
    setResizeHandle(handle);
    resizeStart.current = {
      x: e.clientX,
      y: e.clientY,
      width: size.width,
      height: size.height,
      left: position.x,
      top: position.y
    };

    document.addEventListener('mousemove', handleResizeMove);
    document.addEventListener('mouseup', handleResizeEnd);
  };

  // Handle resize move
  const handleResizeMove = React.useCallback((e) => {
    if (!isResizing) return;

    const deltaX = e.clientX - resizeStart.current.x;
    const deltaY = e.clientY - resizeStart.current.y;

    let newWidth = resizeStart.current.width;
    let newHeight = resizeStart.current.height;
    let newX = position.x;
    let newY = position.y;

    // Handle different resize directions
    if (resizeHandle.includes('e')) {
      newWidth = Math.max(minSize.width, resizeStart.current.width + deltaX);
    }
    if (resizeHandle.includes('w')) {
      const proposedWidth = resizeStart.current.width - deltaX;
      if (proposedWidth >= minSize.width) {
        newWidth = proposedWidth;
        newX = resizeStart.current.left + deltaX;
      }
    }
    if (resizeHandle.includes('s')) {
      newHeight = Math.max(minSize.height, resizeStart.current.height + deltaY);
    }
    if (resizeHandle.includes('n')) {
      const proposedHeight = resizeStart.current.height - deltaY;
      if (proposedHeight >= minSize.height) {
        newHeight = proposedHeight;
        newY = resizeStart.current.top + deltaY;
      }
    }

    setSize({ width: newWidth, height: newHeight });
    if (resizeHandle.includes('w') || resizeHandle.includes('n')) {
      setPosition({ x: newX, y: newY });
    }
  }, [isResizing, resizeHandle, minSize, position]);

  // Handle resize end
  const handleResizeEnd = React.useCallback(() => {
    setIsResizing(false);
    setResizeHandle(null);
    document.removeEventListener('mousemove', handleResizeMove);
    document.removeEventListener('mouseup', handleResizeEnd);
  }, [handleResizeMove]);

  // Toggle maximize
  const toggleMaximize = () => {
    if (isDocked) setIsDocked(false);
    setIsMaximized(!isMaximized);
  };

  // Toggle dock (right side)
  const toggleDock = () => {
    if (isMaximized) setIsMaximized(false);
    const newDocked = !isDocked;
    setIsDocked(newDocked);
    if (onDock) onDock(newDocked);
  };

  // Get panel style
  const getPanelStyle = () => {
    if (isMaximized) {
      return {
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        width: '100vw',
        height: '100vh',
        borderRadius: 0
      };
    }

    if (isDocked) {
      return {
        position: 'fixed',
        top: 0,
        right: 0,
        width: '400px',
        height: '100vh',
        borderRadius: '12px 0 0 12px'
      };
    }

    return {
      position: 'fixed',
      left: position.x,
      top: position.y,
      width: size.width,
      height: size.height
    };
  };

  // Cleanup event listeners on unmount
  React.useEffect(() => {
    return () => {
      document.removeEventListener('mousemove', handleDragMove);
      document.removeEventListener('mouseup', handleDragEnd);
      document.removeEventListener('mousemove', handleResizeMove);
      document.removeEventListener('mouseup', handleResizeEnd);
    };
  }, [handleDragMove, handleDragEnd, handleResizeMove, handleResizeEnd]);

  const panelClasses = [
    'draggable-panel',
    isMaximized ? 'draggable-panel--maximized' : '',
    isDocked ? 'draggable-panel--docked-right' : '',
    className
  ].filter(Boolean).join(' ');

  return (
    <div
      ref={panelRef}
      className={panelClasses}
      style={getPanelStyle()}
    >
      {/* Resize Handles */}
      {!isMaximized && !isDocked && (
        <>
          <div className="draggable-panel__resize-handle draggable-panel__resize-handle--n" onMouseDown={(e) => handleResizeStart(e, 'n')} />
          <div className="draggable-panel__resize-handle draggable-panel__resize-handle--s" onMouseDown={(e) => handleResizeStart(e, 's')} />
          <div className="draggable-panel__resize-handle draggable-panel__resize-handle--e" onMouseDown={(e) => handleResizeStart(e, 'e')} />
          <div className="draggable-panel__resize-handle draggable-panel__resize-handle--w" onMouseDown={(e) => handleResizeStart(e, 'w')} />
          <div className="draggable-panel__resize-handle draggable-panel__resize-handle--ne" onMouseDown={(e) => handleResizeStart(e, 'ne')} />
          <div className="draggable-panel__resize-handle draggable-panel__resize-handle--nw" onMouseDown={(e) => handleResizeStart(e, 'nw')} />
          <div className="draggable-panel__resize-handle draggable-panel__resize-handle--se" onMouseDown={(e) => handleResizeStart(e, 'se')} />
          <div className="draggable-panel__resize-handle draggable-panel__resize-handle--sw" onMouseDown={(e) => handleResizeStart(e, 'sw')} />
        </>
      )}

      {/* Header */}
      <div
        className="draggable-panel__header"
        onMouseDown={handleDragStart}
      >
        <div className="draggable-panel__title">
          {title}
        </div>
        <div className="draggable-panel__actions">
          <button
            className="draggable-panel__btn"
            onClick={toggleDock}
            title={isDocked ? __('Undock') : __('Dock')}
          >
            <i className={`fa fa-${isDocked ? 'window-restore' : 'thumbtack'}`}></i>
          </button>
          <button
            className="draggable-panel__btn"
            onClick={toggleMaximize}
            title={isMaximized ? __('Restore') : __('Maximize')}
          >
            <i className={`fa fa-${isMaximized ? 'compress' : 'expand'}`}></i>
          </button>
          <button
            className="draggable-panel__btn draggable-panel__btn--close"
            onClick={onClose}
            title={__('Close')}
          >
            <i className="fa fa-times"></i>
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="draggable-panel__body">
        {children}
      </div>
    </div>
  );
};

// Export for global access
window.DraggablePanel = DraggablePanel;
