import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QGraphicsView, 
                             QGraphicsScene, QGraphicsItem, QGraphicsEllipseItem, 
                             QGraphicsLineItem, QGraphicsTextItem, QDockWidget, 
                             QListWidget, QListWidgetItem, QToolBar, QAction, 
                             QMessageBox)
from PyQt5.QtCore import Qt, QPointF, QRectF, QLineF, pyqtSignal
from PyQt5.QtGui import QColor, QPen, QBrush, QFont

# Base class for wires, nodes, etc.
class Wire(QGraphicsLineItem):
    """Represents a connection wire between nodes"""
    def __init__(self, source_socket, target_socket, parent=None):
        super().__init__(parent)
        self.source_socket = source_socket
        self.target_socket = target_socket
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setPen(QPen(QColor(200, 200, 200), 2))
        self.update_position()
        print(f"Wire created from {source_socket.node.title} to {target_socket.node.title}")
        
    def update_position(self):
        try:
            if self.source_socket and self.target_socket:
                source_pos = self.source_socket.scenePos() + QPointF(5, 5)
                target_pos = self.target_socket.scenePos() + QPointF(5, 5)
                self.setLine(QLineF(source_pos, target_pos))
        except Exception as e:
            print(f"Error updating wire position: {str(e)}")
            
    def remove(self):
        try:
            if self.source_socket and self in self.source_socket.connections:
                self.source_socket.connections.remove(self)
            if self.target_socket and self in self.target_socket.connections:
                self.target_socket.connections.remove(self)
            if self.scene():
                self.scene().removeItem(self)
        except Exception as e:
            print(f"Error removing wire: {str(e)}")

class Socket(QGraphicsEllipseItem):
    """Represents an input or output socket for a node"""
    def __init__(self, node, socket_type, index=0, parent=None):
        super().__init__(0, 0, 10, 10, parent)
        self.node = node
        self.socket_type = socket_type  # 'input' or 'output'
        self.index = index
        self.connections = []
        self.value = False
        
        # Set appearance
        self.setBrush(QBrush(QColor(0, 0, 0)))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        
        # Temporary line for dragging
        self.temp_line = None
        
    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(QColor(100, 100, 255)))
        super().hoverEnterEvent(event)
        
    def hoverLeaveEvent(self, event):
        if self.value:
            self.setBrush(QBrush(QColor(0, 255, 0)))
        else:
            self.setBrush(QBrush(QColor(0, 0, 0)))
        super().hoverLeaveEvent(event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Start drawing a line
            if self.socket_type == 'output':
                try:
                    scene_pos = self.scenePos() + QPointF(5, 5)
                    self.temp_line = QGraphicsLineItem(QLineF(scene_pos, scene_pos))
                    self.temp_line.setPen(QPen(QColor(200, 200, 200), 2))
                    self.scene().addItem(self.temp_line)
                    event.accept()
                except Exception as e:
                    print(f"Error in Socket.mousePressEvent: {str(e)}")
            super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        if self.temp_line and self.socket_type == 'output':
            try:
                # Update the line to follow the mouse
                start_pos = self.scenePos() + QPointF(5, 5)
                end_pos = event.scenePos()
                self.temp_line.setLine(QLineF(start_pos, end_pos))
                event.accept()
            except Exception as e:
                print(f"Error in Socket.mouseMoveEvent: {str(e)}")
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        if self.temp_line and self.socket_type == 'output':
            try:
                scene = self.scene()
                end_pos = event.scenePos()
                
                # Check if we're over an input socket
                items = scene.items(end_pos)
                found_input = False
                
                for item in items:
                    if isinstance(item, Socket) and item.socket_type == 'input' and item != self:
                        # Don't connect sockets from the same node
                        if item.node != self.node:
                            # Check if the target socket already has a connection
                            if not item.connections:
                                # Create a proper wire
                                wire = Wire(self, item)
                                scene.addItem(wire)
                                self.connections.append(wire)
                                item.connections.append(wire)
                                
                                # Signal nodes to update values
                                self.node.update_outputs()
                                found_input = True
                                print("Connection established")
                                break
                
                if not found_input:
                    print("No compatible input socket found at release position")
            except Exception as e:
                print(f"Error in Socket.mouseReleaseEvent: {str(e)}")
            
            # Remove temporary line
            try:
                if self.temp_line and self.temp_line.scene():
                    scene.removeItem(self.temp_line)
            except Exception as e:
                print(f"Error removing temp_line: {str(e)}")
            
            self.temp_line = None
            event.accept()
        super().mouseReleaseEvent(event)
        
    def get_value(self):
        # For input sockets, get value from connected output socket
        if self.socket_type == 'input' and self.connections:
            source_socket = self.connections[0].source_socket
            return source_socket.node.get_output_value()
        return self.value
        
    def set_value(self, value):
        self.value = value
        if value:
            self.setBrush(QBrush(QColor(0, 255, 0)))
        else:
            self.setBrush(QBrush(QColor(255, 0, 0)))

class Node(QGraphicsItem):
    """Base class for all logic gate nodes"""
    def __init__(self, scene, title, inputs=0, outputs=1, width=150, height=100):
        super().__init__()
        self.scene = scene
        self.title = title
        self.width = width
        self.height = height
        self.title_height = 30
        self.input_sockets = []
        self.output_sockets = []
        
        # Create sockets
        self.init_sockets(inputs, outputs)
        
        # Set flags
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        
    def init_sockets(self, inputs, outputs):
        # Create input sockets
        spacing = self.height / (inputs + 1) if inputs > 0 else 0
        for i in range(inputs):
            socket = Socket(self, 'input', i)
            socket.setParentItem(self)
            socket.setPos(-5, self.title_height + (i + 1) * spacing - 5)
            self.input_sockets.append(socket)
            
        # Create output sockets
        spacing = self.height / (outputs + 1) if outputs > 0 else 0
        for i in range(outputs):
            socket = Socket(self, 'output', i)
            socket.setParentItem(self)
            socket.setPos(self.width - 5, self.title_height + (i + 1) * spacing - 5)
            self.output_sockets.append(socket)
            
    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)
        
    def paint(self, painter, option, widget):
        # Draw node body
        painter.setBrush(QColor(60, 60, 60))
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawRoundedRect(0, 0, self.width, self.height, 10, 10)
        
        # Draw title background
        painter.setBrush(QColor(80, 80, 80))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, self.width, self.title_height, 10, 10)
        painter.drawRect(0, self.title_height - 10, self.width, 10)
        
        # Draw title text
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(QRectF(0, 0, self.width, self.title_height),
                         Qt.AlignCenter, self.title)
                         
    def itemChange(self, change, value):
        # If the position changes, update all connected wires
        if change == QGraphicsItem.ItemPositionChange and self.scene:
            self.updateWires()
        return super().itemChange(change, value)
        
    def updateWires(self):
        """Update position of all wires connected to this node"""
        for socket in self.input_sockets + self.output_sockets:
            for wire in socket.connections:
                wire.update_position()
                         
    def update_outputs(self):
        """Update output values based on inputs"""
        # Calculate output value
        output_value = self.perform_logic()
        
        # Update output socket visuals
        for socket in self.output_sockets:
            socket.set_value(output_value)
            
        # Propagate to connected nodes
        for socket in self.output_sockets:
            for connection in socket.connections:
                target_socket = connection.target_socket
                target_socket.node.update_outputs()
        
    def get_output_value(self):
        """Get the output value of this node"""
        if self.output_sockets:
            return self.output_sockets[0].value
        return False
        
    def perform_logic(self):
        """Perform logic operation and return result"""
        # Should be implemented by subclasses
        return False
        
    def remove(self):
        """Remove this node and all its connections"""
        # Remove all connected wires first
        for socket in self.input_sockets + self.output_sockets:
            for wire in socket.connections[:]:  # Make a copy to avoid modification during iteration
                wire.remove()
        
        # Remove from scene
        if self.scene:
            self.scene.removeItem(self)

class InputNode(Node):
    """Node that allows manual input of a boolean value"""
    def __init__(self, scene):
        super().__init__(scene, "Input", 0, 1)
        self.value = False
        
        # Create a text item for displaying the value
        self.value_text = QGraphicsTextItem(self)
        self.value_text.setPos(10, 40)
        self.value_text.setPlainText(f"Value: {1 if self.value else 0}")
        self.value_text.setDefaultTextColor(QColor(255, 255, 255))
        
    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        
        # Draw a toggle button
        painter.setBrush(QColor(100, 100, 100))
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        # Use QRectF for the rounded rectangle
        painter.drawRoundedRect(QRectF(self.width/2 - 30, 60, 60, 25), 5, 5)
        
        # Draw button text
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRectF(self.width/2 - 30, 60, 60, 25),
                     Qt.AlignCenter, "Toggle")
    
    def mouseReleaseEvent(self, event):
        # Check if click is within toggle button area
        if (self.width/2 - 30 <= event.pos().x() <= self.width/2 + 30 and 
            60 <= event.pos().y() <= 85):
            # Toggle value
            self.value = not self.value
            
            # Update text display
            self.value_text.setPlainText(f"Value: {1 if self.value else 0}")
            
            # Update output socket visual
            if self.output_sockets:
                self.output_sockets[0].set_value(self.value)
                
            # Propagate change to connected nodes
            self.update_outputs()
            
            # Prevent further event propagation
            event.accept()
            return
            
        # Call parent class implementation for other events
        super().mouseReleaseEvent(event)
            
    def get_output_value(self):
        return self.value
        
    def perform_logic(self):
        return self.value

class OutputNode(Node):
    """Node that displays the output value"""
    def __init__(self, scene):
        super().__init__(scene, "Output", 1, 0)
        
    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        
        # Get input value
        input_value = False
        if self.input_sockets and self.input_sockets[0].connections:
            input_value = self.input_sockets[0].get_value()
        
        # Draw node-specific elements
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRectF(10, 40, self.width - 20, 20),
                     Qt.AlignLeft, f"Value: {1 if input_value else 0}")
                     
    def perform_logic(self):
        # This is an output node, so it doesn't compute anything
        return False

class AndGateNode(Node):
    """AND logic gate node"""
    def __init__(self, scene):
        super().__init__(scene, "AND Gate", 2, 1)
        
    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        
        # Draw truth table or symbol
        input1 = self.input_sockets[0].get_value() if self.input_sockets else False
        input2 = self.input_sockets[1].get_value() if len(self.input_sockets) > 1 else False
        output = self.perform_logic()
        
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRectF(10, 40, self.width - 20, 20),
                       Qt.AlignLeft, f"In 1: {1 if input1 else 0}")
        painter.drawText(QRectF(10, 60, self.width - 20, 20),
                       Qt.AlignLeft, f"In 2: {1 if input2 else 0}")
        painter.drawText(QRectF(10, 80, self.width - 20, 20),
                       Qt.AlignLeft, f"Out: {1 if output else 0}")
        
    def perform_logic(self):
        # Get input values
        input1 = self.input_sockets[0].get_value() if self.input_sockets else False
        input2 = self.input_sockets[1].get_value() if len(self.input_sockets) > 1 else False
        
        # AND logic
        return input1 and input2

class OrGateNode(Node):
    """OR logic gate node"""
    def __init__(self, scene):
        super().__init__(scene, "OR Gate", 2, 1)
        
    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        
        # Draw truth table or symbol
        input1 = self.input_sockets[0].get_value() if self.input_sockets else False
        input2 = self.input_sockets[1].get_value() if len(self.input_sockets) > 1 else False
        output = self.perform_logic()
        
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRectF(10, 40, self.width - 20, 20),
                       Qt.AlignLeft, f"In 1: {1 if input1 else 0}")
        painter.drawText(QRectF(10, 60, self.width - 20, 20),
                       Qt.AlignLeft, f"In 2: {1 if input2 else 0}")
        painter.drawText(QRectF(10, 80, self.width - 20, 20),
                       Qt.AlignLeft, f"Out: {1 if output else 0}")
        
    def perform_logic(self):
        # Get input values
        input1 = self.input_sockets[0].get_value() if self.input_sockets else False
        input2 = self.input_sockets[1].get_value() if len(self.input_sockets) > 1 else False
        
        # OR logic
        return input1 or input2

class NotGateNode(Node):
    """NOT logic gate node"""
    def __init__(self, scene):
        super().__init__(scene, "NOT Gate", 1, 1)
        
    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        
        # Draw truth table or symbol
        input1 = self.input_sockets[0].get_value() if self.input_sockets else False
        output = self.perform_logic()
        
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRectF(10, 40, self.width - 20, 20),
                       Qt.AlignLeft, f"In: {1 if input1 else 0}")
        painter.drawText(QRectF(10, 60, self.width - 20, 20),
                       Qt.AlignLeft, f"Out: {1 if output else 0}")
        
    def perform_logic(self):
        # Get input value
        input1 = self.input_sockets[0].get_value() if self.input_sockets else False
        
        # NOT logic
        return not input1

class LogicGateSimulator(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Logic Gate Simulator")
        self.setGeometry(100, 100, 1000, 600)
        
        # Create main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QHBoxLayout(self.central_widget)
        
        # Create sidebar for gate selection
        self.sidebar = QWidget()
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.addWidget(QLabel("<b>Logic Gate Simulator</b>"))
        self.sidebar_layout.addWidget(QLabel("Add Gates:"))
        
        # Create buttons for each gate type
        self.input_btn = QPushButton("Add Input")
        self.output_btn = QPushButton("Add Output")
        self.and_btn = QPushButton("Add AND Gate")
        self.or_btn = QPushButton("Add OR Gate")
        self.not_btn = QPushButton("Add NOT Gate")
        
        self.input_btn.clicked.connect(lambda: self.add_node("input"))
        self.output_btn.clicked.connect(lambda: self.add_node("output"))
        self.and_btn.clicked.connect(lambda: self.add_node("and"))
        self.or_btn.clicked.connect(lambda: self.add_node("or"))
        self.not_btn.clicked.connect(lambda: self.add_node("not"))
        
        self.sidebar_layout.addWidget(self.input_btn)
        self.sidebar_layout.addWidget(self.output_btn)
        self.sidebar_layout.addWidget(self.and_btn)
        self.sidebar_layout.addWidget(self.or_btn)
        self.sidebar_layout.addWidget(self.not_btn)
        
        # Add instructions
        self.sidebar_layout.addWidget(QLabel("<hr>"))
        self.sidebar_layout.addWidget(QLabel("<b>Instructions:</b>"))
        self.sidebar_layout.addWidget(QLabel("1. Add gates using buttons"))
        self.sidebar_layout.addWidget(QLabel("2. Connect gates by dragging from an output socket to an input socket"))
        self.sidebar_layout.addWidget(QLabel("3. Double-click Input nodes to toggle their value"))
        self.sidebar_layout.addWidget(QLabel("4. Delete gates using the Delete button"))
        
        self.sidebar_layout.addStretch(1)  # Add stretch to push buttons to top
        
        # Create a delete button
        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.clicked.connect(self.delete_selected)
        self.sidebar_layout.addWidget(self.delete_btn)
        
        # Create graph view
        self.view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, 5000, 5000)
        self.scene.setBackgroundBrush(QBrush(QColor(40, 40, 40)))
        self.view.setScene(self.scene)
        
        # Setup view properties
        self.view.setRenderHint(0)  # Antialiasing
        self.view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        
        # Add widgets to layout
        self.layout.addWidget(self.sidebar, 1)  # 1 is the stretch factor
        self.layout.addWidget(self.view, 4)     # 4 is the stretch factor
        
        # Setup toolbar
        self.toolbar = QToolBar("Main Toolbar")
        self.addToolBar(self.toolbar)
        
        # Add toolbar actions
        clear_action = QAction("Clear All", self)
        clear_action.triggered.connect(self.clear_scene)
        self.toolbar.addAction(clear_action)
        
        # Show the window
        self.show()
        
    def add_node(self, node_type):
        """Add a new node to the scene"""
        node = None
        
        if node_type == "input":
            node = InputNode(self.scene)
        elif node_type == "output":
            node = OutputNode(self.scene)
        elif node_type == "and":
            node = AndGateNode(self.scene)
        elif node_type == "or":
            node = OrGateNode(self.scene)
        elif node_type == "not":
            node = NotGateNode(self.scene)
            
        if node:
            # Position the node in the center of the visible scene
            view_center = self.view.mapToScene(self.view.viewport().rect().center())
            node.setPos(view_center)
            self.scene.addItem(node)
            print(f"Added {node_type} node to scene")
            
    def delete_selected(self):
        """Delete selected items from the scene"""
        for item in self.scene.selectedItems():
            if isinstance(item, Node):
                item.remove()
            elif isinstance(item, Wire):
                item.remove()
                
    def clear_scene(self):
        """Clear all items from the scene"""
        for item in self.scene.items():
            if isinstance(item, Node) or isinstance(item, Wire):
                self.scene.removeItem(item)
                

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LogicGateSimulator()
    sys.exit(app.exec_()) 