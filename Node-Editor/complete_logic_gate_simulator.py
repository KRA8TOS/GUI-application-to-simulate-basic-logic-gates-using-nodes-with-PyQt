import sys
import os
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTabWidget, QAction, QMenu, QToolBar, 
                            QLabel, QLineEdit, QPushButton, QFileDialog, QColorDialog,
                            QComboBox, QGraphicsView, QGraphicsScene, 
                            QGraphicsItem, QGraphicsEllipseItem, QGraphicsLineItem,
                            QGraphicsPathItem, QGraphicsTextItem, QDockWidget, 
                            QListWidget, QListWidgetItem, QMessageBox, QUndoCommand,
                            QUndoStack)
from PyQt5.QtCore import (Qt, QPointF, QRectF, QLineF, pyqtSignal, 
                         QMimeData, QObject, QEvent, QSize, QByteArray,
                         QDataStream, QIODevice, QPoint)
from PyQt5.QtGui import (QColor, QPen, QBrush, QFont, QDrag, 
                        QPixmap, QPainter, QPainterPath, QKeyEvent, QCursor, QKeySequence)

# Base classes for wires, nodes, etc.
class Wire(QGraphicsLineItem):
    """Represents a connection wire between nodes"""
    def __init__(self, source_socket, target_socket, parent=None):
        super().__init__(parent)
        self.source_socket = source_socket
        self.target_socket = target_socket
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setPen(QPen(QColor(200, 200, 200), 2))
        self.update_position()
        
        # Connect to sockets
        self.source_socket.wires.append(self)
        self.target_socket.wires.append(self)
        
        # Add to scene - must be added by the caller
        
    def update_position(self):
        """Update the position of the wire based on socket positions"""
        if self.source_socket and self.target_socket:
            source_pos = self.source_socket.scenePos() + QPointF(5, 5)
            target_pos = self.target_socket.scenePos() + QPointF(5, 5)
            self.setLine(QLineF(source_pos, target_pos))
            
    def remove(self):
        """Remove this wire and disconnect it from sockets"""
        # Remove from sockets
        if self.source_socket and self in self.source_socket.wires:
            self.source_socket.wires.remove(self)
        if self.target_socket and self in self.target_socket.wires:
            self.target_socket.wires.remove(self)
        
        # Remove from scene
        try:
            if self.scene():
                self.scene().removeItem(self)
        except:
            # Just ignore errors
            pass

class Socket(QGraphicsEllipseItem):
    """Socket for node connections"""
    def __init__(self, parent_node, is_output=False):
        super().__init__(parent_node)
        self.parent_node = parent_node
        self.is_output = is_output
        self.wires = []  # List of connected wires
        self.value = False
        self.temp_line = None
        
        # Set visual properties
        self.setRect(-5, -5, 10, 10)
        self.setBrush(QBrush(QColor(50, 50, 50)))
        self.setPen(QPen(QColor(200, 200, 200), 1))
        
        # Mouse interaction
        self.setAcceptHoverEvents(True)
        
    def get_value(self):
        """Get the value of this socket"""
        if not self.is_output and self.wires:
            # Input socket - get value from connected output
            return self.wires[0].source_socket.value
        return self.value
        
    def updateValue(self, value):
        """Update the socket value and visual state"""
        if self.value != value:
            self.value = value
            
            # Update visual appearance
            if value:
                self.setBrush(QBrush(QColor(0, 255, 0)))  # Green for true
            else:
                self.setBrush(QBrush(QColor(50, 50, 50)))  # Gray for false
                
            # Propagate to connected nodes if this is an output socket
            if self.is_output:
                for wire in self.wires:
                    # Update the input node's logic
                    wire.target_socket.parent_node.updateLogic()
        
    def hoverEnterEvent(self, event):
        """Highlight socket on hover"""
        self.setBrush(QBrush(QColor(255, 255, 100)))  # Yellow highlight
        super().hoverEnterEvent(event)
        
    def hoverLeaveEvent(self, event):
        """Restore socket color on hover leave"""
        if self.value:
            self.setBrush(QBrush(QColor(0, 255, 0)))  # Green for true
        else:
            self.setBrush(QBrush(QColor(50, 50, 50)))  # Gray for false
        super().hoverLeaveEvent(event)
        
    def mousePressEvent(self, event):
        """Start wire creation on mouse press"""
        if event.button() == Qt.LeftButton:
            # Start drawing a line
            scene_pos = self.scenePos() + QPointF(5, 5)
            self.temp_line = QGraphicsLineItem(QLineF(scene_pos, scene_pos))
            self.temp_line.setPen(QPen(QColor(200, 200, 200), 2))
            self.scene().addItem(self.temp_line)
            event.accept()
        else:
            super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        """Update temporary line during mouse movement"""
        if self.temp_line:
            # Update the line to follow the mouse
            start_pos = self.scenePos() + QPointF(5, 5)
            end_pos = self.mapToScene(event.pos())
            self.temp_line.setLine(QLineF(start_pos, end_pos))
            event.accept()
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        """Handle connection completion on mouse release"""
        if self.temp_line:
            try:
                # Find if we're over another socket
                end_pos = self.mapToScene(event.pos())
                items = self.scene().items(end_pos)
                
                target_socket = None
                for item in items:
                    if isinstance(item, Socket) and item != self:
                        # Check if connection makes sense (output to input)
                        if self.is_output and not item.is_output:
                            # Output to input
                            source_socket = self
                            target_socket = item
                        elif not self.is_output and item.is_output:
                            # Input to output
                            source_socket = item
                            target_socket = self
                        else:
                            # Invalid connection (output to output or input to input)
                            continue
                            
                        # Don't connect to self
                        if source_socket.parent_node == target_socket.parent_node:
                            continue
                            
                        # Remove existing connections to the target input
                        if not target_socket.is_output and target_socket.wires:
                            for wire in list(target_socket.wires):
                                wire.remove()
                        
                        # Create wire and add to scene
                        wire = Wire(source_socket, target_socket)
                        
                        # Only add to scene if not already in a scene
                        if not wire.scene():
                            self.scene().addItem(wire)
                            
                        print(f"Connected {source_socket.parent_node.title} to {target_socket.parent_node.title}")
                        
                        # Update logic
                        target_socket.parent_node.updateLogic()
                        break
            
            finally:
                # Always remove the temporary line
                if self.temp_line and self.temp_line.scene():
                    self.scene().removeItem(self.temp_line)
                self.temp_line = None
                
            event.accept()
        else:
            super().mouseReleaseEvent(event)

class Node(QGraphicsItem):
    """Base class for all nodes"""
    
    def __init__(self, scene, title="Node"):
        super().__init__()
        self.scene = scene
        self.title = title
        self.width = 150
        self.height = 120
        self.title_height = 30
        self.input_sockets = []
        self.output_sockets = []
        
        # Set flags
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        
        # Create sockets - will be overridden by subclasses
        
        # Don't add to scene here, let the caller handle it
        # scene.addItem(self)
        
    def boundingRect(self):
        """Define the bounding rectangle of the node"""
        return QRectF(0, 0, self.width, self.height)
        
    def paint(self, painter, option, widget):
        """Paint the node's appearance"""
        # Draw node body
        painter.setBrush(QBrush(QColor(60, 60, 60)))
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawRoundedRect(0, 0, self.width, self.height, 10, 10)
        
        # Draw title background
        painter.setBrush(QBrush(QColor(80, 80, 80)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, self.width, self.title_height, 10, 10)
        painter.drawRect(0, self.title_height - 10, self.width, 10)
        
        # Draw title text
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(QRectF(0, 0, self.width, self.title_height), 
                         Qt.AlignCenter, self.title)
                         
    def itemChange(self, change, value):
        """Handle item changes such as position changes"""
        if change == QGraphicsItem.ItemPositionChange:
            self.updateWires()
        return super().itemChange(change, value)
        
    def updateWires(self):
        """Update the position of all connected wires"""
        for socket in self.input_sockets + self.output_sockets:
            for wire in socket.wires:
                wire.update_position()
                
    def updateLogic(self):
        """Update the logic and propagate changes to connected nodes"""
        # Override in subclasses
        pass

# Node implementations

class InputNode(Node):
    """Input node that provides a boolean value"""
    
    def __init__(self, scene):
        super().__init__(scene, "Input")
        self.value = False
        
        # Create output socket
        output_socket = Socket(self, is_output=True)
        output_socket.setPos(self.width, self.height / 2)
        self.output_sockets.append(output_socket)
        
        # Create text item to display value
        self.value_text = QGraphicsTextItem("Value: 0", self)
        self.value_text.setPos(20, 50)
        self.value_text.setDefaultTextColor(QColor(255, 255, 255))
        
    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        
        # Draw a toggle button
        button_rect = QRectF(20, 70, self.width - 40, 30)
        
        # Button background
        painter.setBrush(QBrush(QColor(100, 100, 150)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(button_rect, 5, 5)
        
        # Button text
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setFont(QFont("Arial", 10))
        painter.drawText(button_rect, Qt.AlignCenter, "Toggle")
        
    def mouseReleaseEvent(self, event):
        """Handle mouse click to toggle the input value"""
        # Check if click is within the toggle button area
        button_rect = QRectF(20, 70, self.width - 40, 30)
        
        if button_rect.contains(event.pos()):
            # Toggle the value
            self.value = not self.value
            
            # Update the text display
            self.value_text.setPlainText(f"Value: {1 if self.value else 0}")
            
            # Update output socket
            if self.output_sockets:
                print(f"Input node '{self.title}' toggled to {self.value}")
                self.output_sockets[0].updateValue(self.value)
                
                # Propagate the change to all connected nodes
                for wire in self.output_sockets[0].wires:
                    wire.target_socket.parent_node.updateLogic()
                
            event.accept()
            return
            
        super().mouseReleaseEvent(event)
        
    def updateLogic(self):
        """Update output values and propagate changes"""
        if self.output_sockets:
            self.output_sockets[0].updateValue(self.value)

class OutputNode(Node):
    """Node that displays the output value"""
    def __init__(self, scene, write_to_file=False):
        title = "Write Output" if write_to_file else "Output"
        super().__init__(scene, title)
        self.write_to_file = write_to_file
        
        # Create input socket
        input_socket = Socket(self, is_output=False)
        input_socket.setPos(0, self.height / 2)
        self.input_sockets.append(input_socket)
        
        # Create text item to display value
        self.value_text = QGraphicsTextItem("Value: 0", self)
        self.value_text.setPos(20, 40)
        self.value_text.setDefaultTextColor(QColor(255, 255, 255))
        
    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        
        # Draw the current value from connected inputs
        value = self.get_value()
        
        # Update the text display
        self.value_text.setPlainText(f"Value: {1 if value else 0}")
        
        # Draw a save button if this is a write output node
        if self.write_to_file:
            # Button background
            button_rect = QRectF(20, 70, self.width - 40, 30)
            painter.setBrush(QBrush(QColor(100, 100, 150)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(button_rect, 5, 5)
            
            # Button text
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.setFont(QFont("Arial", 10))
            painter.drawText(button_rect, Qt.AlignCenter, "Save to File")
        
    def mouseReleaseEvent(self, event):
        """Handle mouse click to save output to file if this is a Write Output node"""
        if self.write_to_file:
            # Check if click is within the button area
            button_rect = QRectF(20, 70, self.width - 40, 30)
            
            if button_rect.contains(event.pos()):
                self.save_to_file()
                event.accept()
                return
        
        super().mouseReleaseEvent(event)
        
    def save_to_file(self):
        """Save the current output value to a text file"""
        try:
            value = self.get_value()
            
            # Get a file path to save to
            file_path, _ = QFileDialog.getSaveFileName(None, "Save Output", "", "Text Files (*.txt)")
            
            if file_path:
                with open(file_path, 'w') as f:
                    f.write(f"Output Value: {1 if value else 0}")
                    
                print(f"Saved output value {1 if value else 0} to {file_path}")
                QMessageBox.information(None, "Success", f"Output value saved to {file_path}")
        except Exception as e:
            print(f"Error saving to file: {str(e)}")
            QMessageBox.critical(None, "Error", f"Failed to save: {str(e)}")
        
    def get_value(self):
        """Get the input value connected to this output node"""
        if self.input_sockets and self.input_sockets[0].wires:
            wire = self.input_sockets[0].wires[0]
            return wire.source_socket.value
            
        return False
        
    def updateLogic(self):
        """Update the displayed value"""
        self.update()

class AndGateNode(Node):
    """AND gate logic node"""
    def __init__(self, scene):
        super().__init__(scene, "AND")
        
        # Create input sockets
        input1 = Socket(self, is_output=False)
        input1.setPos(0, self.height / 3)
        self.input_sockets.append(input1)
        
        input2 = Socket(self, is_output=False)
        input2.setPos(0, 2 * self.height / 3)
        self.input_sockets.append(input2)
        
        # Create output socket
        output = Socket(self, is_output=True)
        output.setPos(self.width, self.height / 2)
        self.output_sockets.append(output)
        
    def paint(self, painter, option, widget):
        """Paint the node with AND gate symbol"""
        # Draw the basic node
        super().paint(painter, option, widget)
        
        # Draw AND gate symbol
        symbol_rect = QRectF(self.width / 2 - 25, self.height / 2 - 20, 50, 40)
        
        path = QPainterPath()
        path.moveTo(symbol_rect.left(), symbol_rect.top())
        path.lineTo(symbol_rect.left(), symbol_rect.bottom())
        path.lineTo(symbol_rect.center().x(), symbol_rect.bottom())
        path.arcTo(
            symbol_rect.center().x() - 20, 
            symbol_rect.top(),
            40, 
            symbol_rect.height(),
            -90, 180
        )
        path.lineTo(symbol_rect.left(), symbol_rect.top())
        
        painter.setBrush(QBrush(QColor(80, 80, 100)))
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.drawPath(path)
        
        # Draw connectors
        painter.drawLine(
            QPointF(0, self.height / 3),
            QPointF(symbol_rect.left(), self.height / 3)
        )
        painter.drawLine(
            QPointF(0, 2 * self.height / 3),
            QPointF(symbol_rect.left(), 2 * self.height / 3)
        )
        painter.drawLine(
            QPointF(symbol_rect.right(), self.height / 2),
            QPointF(self.width, self.height / 2)
        )
        
    def updateLogic(self):
        """Update output value based on AND logic"""
        # Get input values
        input1_value = False
        input2_value = False
        
        if self.input_sockets and len(self.input_sockets) > 0 and self.input_sockets[0].wires:
            input1_value = self.input_sockets[0].wires[0].source_socket.value
            
        if self.input_sockets and len(self.input_sockets) > 1 and self.input_sockets[1].wires:
            input2_value = self.input_sockets[1].wires[0].source_socket.value
            
        # Perform AND logic
        output_value = input1_value and input2_value
        
        # Update output socket
        if self.output_sockets:
            self.output_sockets[0].updateValue(output_value)

class OrGateNode(Node):
    """OR gate logic node"""
    def __init__(self, scene):
        super().__init__(scene, "OR")
        
        # Create input sockets
        input1 = Socket(self, is_output=False)
        input1.setPos(0, self.height / 3)
        self.input_sockets.append(input1)
        
        input2 = Socket(self, is_output=False)
        input2.setPos(0, 2 * self.height / 3)
        self.input_sockets.append(input2)
        
        # Create output socket
        output = Socket(self, is_output=True)
        output.setPos(self.width, self.height / 2)
        self.output_sockets.append(output)
        
    def paint(self, painter, option, widget):
        """Paint the node with OR gate symbol"""
        # Draw the basic node
        super().paint(painter, option, widget)
        
        # Draw OR gate symbol
        symbol_rect = QRectF(self.width / 2 - 25, self.height / 2 - 20, 50, 40)
        
        path = QPainterPath()
        path.moveTo(symbol_rect.left(), symbol_rect.top())
        path.quadTo(
            symbol_rect.left() + 5, symbol_rect.center().y(),
            symbol_rect.left(), symbol_rect.bottom()
        )
        path.quadTo(
            symbol_rect.left() + 20, symbol_rect.bottom(),
            symbol_rect.right(), symbol_rect.center().y()
        )
        path.quadTo(
            symbol_rect.left() + 20, symbol_rect.top(),
            symbol_rect.left(), symbol_rect.top()
        )
        
        painter.setBrush(QBrush(QColor(80, 80, 100)))
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.drawPath(path)
        
        # Draw connectors
        painter.drawLine(
            QPointF(0, self.height / 3),
            QPointF(symbol_rect.left() + 5, self.height / 3)
        )
        painter.drawLine(
            QPointF(0, 2 * self.height / 3),
            QPointF(symbol_rect.left() + 5, 2 * self.height / 3)
        )
        painter.drawLine(
            QPointF(symbol_rect.right(), self.height / 2),
            QPointF(self.width, self.height / 2)
        )
        
    def updateLogic(self):
        """Update output value based on OR logic"""
        # Get input values
        input1_value = False
        input2_value = False
        
        if self.input_sockets and len(self.input_sockets) > 0 and self.input_sockets[0].wires:
            input1_value = self.input_sockets[0].wires[0].source_socket.value
            
        if self.input_sockets and len(self.input_sockets) > 1 and self.input_sockets[1].wires:
            input2_value = self.input_sockets[1].wires[0].source_socket.value
            
        # Perform OR logic
        output_value = input1_value or input2_value
        
        # Update output socket
        if self.output_sockets:
            self.output_sockets[0].updateValue(output_value)

class NotGateNode(Node):
    """NOT gate logic node"""
    def __init__(self, scene):
        super().__init__(scene, "NOT")
        
        # Create input socket
        input1 = Socket(self, is_output=False)
        input1.setPos(0, self.height / 2)
        self.input_sockets.append(input1)
        
        # Create output socket
        output = Socket(self, is_output=True)
        output.setPos(self.width, self.height / 2)
        self.output_sockets.append(output)
        
    def paint(self, painter, option, widget):
        """Paint the node with NOT gate symbol"""
        # Draw the basic node
        super().paint(painter, option, widget)
        
        # Draw NOT gate symbol
        symbol_rect = QRectF(self.width / 2 - 20, self.height / 2 - 15, 40, 30)
        
        # Triangle
        path = QPainterPath()
        path.moveTo(symbol_rect.left(), symbol_rect.top())
        path.lineTo(symbol_rect.left(), symbol_rect.bottom())
        path.lineTo(symbol_rect.right() - 10, symbol_rect.center().y())
        path.lineTo(symbol_rect.left(), symbol_rect.top())
        
        painter.setBrush(QBrush(QColor(80, 80, 100)))
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.drawPath(path)
        
        # Inverter circle
        painter.drawEllipse(QRectF(
            symbol_rect.right() - 10, 
            symbol_rect.center().y() - 5,
            10, 10
        ))
        
        # Draw connectors
        painter.drawLine(
            QPointF(0, self.height / 2),
            QPointF(symbol_rect.left(), self.height / 2)
        )
        painter.drawLine(
            QPointF(symbol_rect.right(), self.height / 2),
            QPointF(self.width, self.height / 2)
        )
        
    def updateLogic(self):
        """Update output value based on NOT logic"""
        # Get input value
        input_value = False
        
        if self.input_sockets and self.input_sockets[0].wires:
            input_value = self.input_sockets[0].wires[0].source_socket.value
            
        # Perform NOT logic
        output_value = not input_value
        
        # Update output socket
        if self.output_sockets:
            self.output_sockets[0].updateValue(output_value)

class NandGateNode(Node):
    """NAND gate logic node"""
    def __init__(self, scene):
        super().__init__(scene, "NAND")
        
        # Create input sockets
        input1 = Socket(self, is_output=False)
        input1.setPos(0, self.height / 3)
        self.input_sockets.append(input1)
        
        input2 = Socket(self, is_output=False)
        input2.setPos(0, 2 * self.height / 3)
        self.input_sockets.append(input2)
        
        # Create output socket
        output = Socket(self, is_output=True)
        output.setPos(self.width, self.height / 2)
        self.output_sockets.append(output)
        
    def paint(self, painter, option, widget):
        """Paint the node with NAND gate symbol"""
        # Draw the basic node
        super().paint(painter, option, widget)
        
        # Draw NAND gate symbol
        symbol_rect = QRectF(self.width / 2 - 25, self.height / 2 - 20, 40, 40)
        
        # AND part
        path = QPainterPath()
        path.moveTo(symbol_rect.left(), symbol_rect.top())
        path.lineTo(symbol_rect.left(), symbol_rect.bottom())
        path.lineTo(symbol_rect.center().x(), symbol_rect.bottom())
        path.arcTo(
            symbol_rect.center().x() - 20, 
            symbol_rect.top(),
            40, 
            symbol_rect.height(),
            -90, 180
        )
        path.lineTo(symbol_rect.left(), symbol_rect.top())
        
        painter.setBrush(QBrush(QColor(80, 80, 100)))
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.drawPath(path)
        
        # Inverter circle
        painter.drawEllipse(QRectF(
            symbol_rect.right(), 
            symbol_rect.center().y() - 5,
            10, 10
        ))
        
        # Draw connectors
        painter.drawLine(
            QPointF(0, self.height / 3),
            QPointF(symbol_rect.left(), self.height / 3)
        )
        painter.drawLine(
            QPointF(0, 2 * self.height / 3),
            QPointF(symbol_rect.left(), 2 * self.height / 3)
        )
        painter.drawLine(
            QPointF(symbol_rect.right() + 10, self.height / 2),
            QPointF(self.width, self.height / 2)
        )
        
    def updateLogic(self):
        """Update output value based on NAND logic"""
        # Get input values
        input1_value = False
        input2_value = False
        
        if self.input_sockets and len(self.input_sockets) > 0 and self.input_sockets[0].wires:
            input1_value = self.input_sockets[0].wires[0].source_socket.value
            
        if self.input_sockets and len(self.input_sockets) > 1 and self.input_sockets[1].wires:
            input2_value = self.input_sockets[1].wires[0].source_socket.value
            
        # Perform NAND logic
        output_value = not (input1_value and input2_value)
        
        # Update output socket
        if self.output_sockets:
            self.output_sockets[0].updateValue(output_value)

class NorGateNode(Node):
    """NOR gate logic node"""
    def __init__(self, scene):
        super().__init__(scene, "NOR")
        
        # Create input sockets
        input1 = Socket(self, is_output=False)
        input1.setPos(0, self.height / 3)
        self.input_sockets.append(input1)
        
        input2 = Socket(self, is_output=False)
        input2.setPos(0, 2 * self.height / 3)
        self.input_sockets.append(input2)
        
        # Create output socket
        output = Socket(self, is_output=True)
        output.setPos(self.width, self.height / 2)
        self.output_sockets.append(output)
        
    def paint(self, painter, option, widget):
        """Paint the node with NOR gate symbol"""
        # Draw the basic node
        super().paint(painter, option, widget)
        
        # Draw NOR gate symbol
        symbol_rect = QRectF(self.width / 2 - 25, self.height / 2 - 20, 40, 40)
        
        # OR part
        path = QPainterPath()
        path.moveTo(symbol_rect.left(), symbol_rect.top())
        path.quadTo(
            symbol_rect.left() + 5, symbol_rect.center().y(),
            symbol_rect.left(), symbol_rect.bottom()
        )
        path.quadTo(
            symbol_rect.left() + 20, symbol_rect.bottom(),
            symbol_rect.right() - 10, symbol_rect.center().y()
        )
        path.quadTo(
            symbol_rect.left() + 20, symbol_rect.top(),
            symbol_rect.left(), symbol_rect.top()
        )
        
        painter.setBrush(QBrush(QColor(80, 80, 100)))
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.drawPath(path)
        
        # Inverter circle
        painter.drawEllipse(QRectF(
            symbol_rect.right() - 10, 
            symbol_rect.center().y() - 5,
            10, 10
        ))
        
        # Draw connectors
        painter.drawLine(
            QPointF(0, self.height / 3),
            QPointF(symbol_rect.left() + 5, self.height / 3)
        )
        painter.drawLine(
            QPointF(0, 2 * self.height / 3),
            QPointF(symbol_rect.left() + 5, 2 * self.height / 3)
        )
        painter.drawLine(
            QPointF(symbol_rect.right(), self.height / 2),
            QPointF(self.width, self.height / 2)
        )
        
    def updateLogic(self):
        """Update output value based on NOR logic"""
        # Get input values
        input1_value = False
        input2_value = False
        
        if self.input_sockets and len(self.input_sockets) > 0 and self.input_sockets[0].wires:
            input1_value = self.input_sockets[0].wires[0].source_socket.value
            
        if self.input_sockets and len(self.input_sockets) > 1 and self.input_sockets[1].wires:
            input2_value = self.input_sockets[1].wires[0].source_socket.value
            
        # Perform NOR logic
        output_value = not (input1_value or input2_value)
        
        # Update output socket
        if self.output_sockets:
            self.output_sockets[0].updateValue(output_value)

class XorGateNode(Node):
    """XOR gate logic node"""
    def __init__(self, scene):
        super().__init__(scene, "XOR")
        
        # Create input sockets
        input1 = Socket(self, is_output=False)
        input1.setPos(0, self.height / 3)
        self.input_sockets.append(input1)
        
        input2 = Socket(self, is_output=False)
        input2.setPos(0, 2 * self.height / 3)
        self.input_sockets.append(input2)
        
        # Create output socket
        output = Socket(self, is_output=True)
        output.setPos(self.width, self.height / 2)
        self.output_sockets.append(output)
        
    def paint(self, painter, option, widget):
        """Paint the node with XOR gate symbol"""
        # Draw the basic node
        super().paint(painter, option, widget)
        
        # Draw XOR gate symbol
        symbol_rect = QRectF(self.width / 2 - 25, self.height / 2 - 20, 50, 40)
        
        # Double curved line for XOR
        path = QPainterPath()
        path.moveTo(symbol_rect.left() + 5, symbol_rect.top())
        path.quadTo(
            symbol_rect.left() + 10, symbol_rect.center().y(),
            symbol_rect.left() + 5, symbol_rect.bottom()
        )
        
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.drawPath(path)
        
        # OR part
        path = QPainterPath()
        path.moveTo(symbol_rect.left() + 10, symbol_rect.top())
        path.quadTo(
            symbol_rect.left() + 15, symbol_rect.center().y(),
            symbol_rect.left() + 10, symbol_rect.bottom()
        )
        path.quadTo(
            symbol_rect.left() + 30, symbol_rect.bottom(),
            symbol_rect.right(), symbol_rect.center().y()
        )
        path.quadTo(
            symbol_rect.left() + 30, symbol_rect.top(),
            symbol_rect.left() + 10, symbol_rect.top()
        )
        
        painter.setBrush(QBrush(QColor(80, 80, 100)))
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.drawPath(path)
        
        # Draw connectors
        painter.drawLine(
            QPointF(0, self.height / 3),
            QPointF(symbol_rect.left() + 5, self.height / 3)
        )
        painter.drawLine(
            QPointF(0, 2 * self.height / 3),
            QPointF(symbol_rect.left() + 5, 2 * self.height / 3)
        )
        painter.drawLine(
            QPointF(symbol_rect.right(), self.height / 2),
            QPointF(self.width, self.height / 2)
        )
        
    def updateLogic(self):
        """Update output value based on XOR logic"""
        # Get input values
        input1_value = False
        input2_value = False
        
        if self.input_sockets and len(self.input_sockets) > 0 and self.input_sockets[0].wires:
            input1_value = self.input_sockets[0].wires[0].source_socket.value
            
        if self.input_sockets and len(self.input_sockets) > 1 and self.input_sockets[1].wires:
            input2_value = self.input_sockets[1].wires[0].source_socket.value
            
        # Perform XOR logic
        output_value = input1_value != input2_value
        
        # Update output socket
        if self.output_sockets:
            self.output_sockets[0].updateValue(output_value)

class XnorGateNode(Node):
    """XNOR gate logic node"""
    def __init__(self, scene):
        super().__init__(scene, "XNOR")
        
        # Create input sockets
        input1 = Socket(self, is_output=False)
        input1.setPos(0, self.height / 3)
        self.input_sockets.append(input1)
        
        input2 = Socket(self, is_output=False)
        input2.setPos(0, 2 * self.height / 3)
        self.input_sockets.append(input2)
        
        # Create output socket
        output = Socket(self, is_output=True)
        output.setPos(self.width, self.height / 2)
        self.output_sockets.append(output)
        
    def paint(self, painter, option, widget):
        """Paint the node with XNOR gate symbol"""
        # Draw the basic node
        super().paint(painter, option, widget)
        
        # Draw XNOR gate symbol
        symbol_rect = QRectF(self.width / 2 - 25, self.height / 2 - 20, 40, 40)
        
        # Double curved line for XOR part
        path = QPainterPath()
        path.moveTo(symbol_rect.left() + 5, symbol_rect.top())
        path.quadTo(
            symbol_rect.left() + 10, symbol_rect.center().y(),
            symbol_rect.left() + 5, symbol_rect.bottom()
        )
        
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.drawPath(path)
        
        # OR part with output circle
        path = QPainterPath()
        path.moveTo(symbol_rect.left() + 10, symbol_rect.top())
        path.quadTo(
            symbol_rect.left() + 15, symbol_rect.center().y(),
            symbol_rect.left() + 10, symbol_rect.bottom()
        )
        path.quadTo(
            symbol_rect.left() + 30, symbol_rect.bottom(),
            symbol_rect.right() - 10, symbol_rect.center().y()
        )
        path.quadTo(
            symbol_rect.left() + 30, symbol_rect.top(),
            symbol_rect.left() + 10, symbol_rect.top()
        )
        
        painter.setBrush(QBrush(QColor(80, 80, 100)))
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.drawPath(path)
        
        # Inverter circle
        painter.drawEllipse(QRectF(
            symbol_rect.right() - 10, 
            symbol_rect.center().y() - 5,
            10, 10
        ))
        
        # Draw connectors
        painter.drawLine(
            QPointF(0, self.height / 3),
            QPointF(symbol_rect.left() + 5, self.height / 3)
        )
        painter.drawLine(
            QPointF(0, 2 * self.height / 3),
            QPointF(symbol_rect.left() + 5, 2 * self.height / 3)
        )
        painter.drawLine(
            QPointF(symbol_rect.right(), self.height / 2),
            QPointF(self.width, self.height / 2)
        )
        
    def updateLogic(self):
        """Update output value based on XNOR logic"""
        # Get input values
        input1_value = False
        input2_value = False
        
        if self.input_sockets and len(self.input_sockets) > 0 and self.input_sockets[0].wires:
            input1_value = self.input_sockets[0].wires[0].source_socket.value
            
        if self.input_sockets and len(self.input_sockets) > 1 and self.input_sockets[1].wires:
            input2_value = self.input_sockets[1].wires[0].source_socket.value
            
        # Perform XNOR logic
        output_value = input1_value == input2_value
        
        # Update output socket
        if self.output_sockets:
            self.output_sockets[0].updateValue(output_value)

# UI Components for Node Editor

class NodeListWidget(QListWidget):
    """Widget displaying available node types"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set widget properties
        self.setDragEnabled(True)
        self.setIconSize(QSize(32, 32))
        
        # Add node types
        self.add_node_type("INPUT", "Input Node")
        self.add_node_type("OUTPUT", "Output Node")
        self.add_node_type("AND", "AND Gate")
        self.add_node_type("OR", "OR Gate")
        self.add_node_type("NOT", "NOT Gate")
        self.add_node_type("NAND", "NAND Gate")
        self.add_node_type("NOR", "NOR Gate")
        self.add_node_type("XOR", "XOR Gate")
        self.add_node_type("XNOR", "XNOR Gate")
        
    def add_node_type(self, node_id, name):
        """Add a node type to the list"""
        item = QListWidgetItem(name)
        item.setData(Qt.UserRole, node_id)
        self.addItem(item)
        
    def startDrag(self, supported_actions):
        """Handle the start of a drag operation"""
        try:
            item = self.currentItem()
            if not item:
                return
                
            # Get the node ID stored in the item
            node_id = item.data(Qt.UserRole)
            if not node_id:
                return
                
            # Create mime data with node ID
            mime_data = QMimeData()
            
            # Convert to QByteArray and use QDataStream
            data = QByteArray()
            stream = QDataStream(data, QIODevice.WriteOnly)
            stream.writeQString(node_id)
            mime_data.setData("application/x-node", data)
            
            # Create drag object
            drag = QDrag(self)
            drag.setMimeData(mime_data)
            
            # Create an icon for the drag operation
            pixmap = self.create_drag_pixmap(item)
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
            
            # Start the drag
            drag.exec_(Qt.CopyAction)
        except Exception as e:
            print(f"Error in NodeListWidget.startDrag: {str(e)}")
            
    def create_drag_pixmap(self, item):
        """Create a pixmap for the drag icon"""
        # Create a pixmap to draw on
        pixmap = QPixmap(100, 50)
        pixmap.fill(Qt.transparent)
        
        # Create a painter for the pixmap
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw a simple representation of the node
        painter.setBrush(QBrush(QColor(70, 70, 80)))
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawRoundedRect(0, 0, 100, 50, 5, 5)
        
        # Draw a title bar
        painter.setBrush(QBrush(QColor(50, 50, 60)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 100, 24, 5, 5)
        painter.drawRect(0, 10, 100, 14)
        
        # Draw the title text
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.setFont(QFont("Arial", 10))
        painter.drawText(0, 0, 100, 24, Qt.AlignCenter, item.text())
        
        # End painting
        painter.end()
        
        return pixmap

class NodeEditorScene(QGraphicsScene):
    """Custom scene for the node editor"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set scene properties
        self.setSceneRect(-1000, -1000, 2000, 2000)
        self.setBackgroundBrush(QBrush(QColor(40, 40, 40)))

class NodeEditorView(QGraphicsView):
    """Custom view for the node editor"""
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setAcceptDrops(True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        # Set scene background
        self.setBackgroundBrush(QBrush(QColor(40, 40, 40)))
        
        # Initialize members
        self.scale_factor = 1.2
        self.current_wire = None
        self.copied_nodes = []
        self.copied_connections = []  # Initialize this attribute in the constructor
        self.copy_offset = 20  # Offset for pasted nodes
        
        # Initialize undo stack for undo/redo
        self.undo_stack = QUndoStack(self)
        
    def create_node(self, node_id, pos):
        """Create a node based on its type ID"""
        node = None
        
        if node_id == "INPUT":
            node = InputNode(self.scene())
        elif node_id == "OUTPUT":
            node = OutputNode(self.scene())
        elif node_id == "AND":
            node = AndGateNode(self.scene())
        elif node_id == "OR":
            node = OrGateNode(self.scene())
        elif node_id == "NOT":
            node = NotGateNode(self.scene())
        elif node_id == "NAND":
            node = NandGateNode(self.scene())
        elif node_id == "NOR":
            node = NorGateNode(self.scene())
        elif node_id == "XOR":
            node = XorGateNode(self.scene())
        elif node_id == "XNOR":
            node = XnorGateNode(self.scene())
            
        if node:
            # Add node to scene
            self.scene().addItem(node)
            
            # Center the node at the drop position
            node.setPos(pos.x() - node.boundingRect().width()/2, 
                        pos.y() - node.boundingRect().height()/2)
                        
            # Register action for undo/redo
            class AddNodeCommand(QUndoCommand):
                def __init__(self, scene, node):
                    super().__init__("Add Node")
                    self.scene = scene
                    self.node = node
                    
                def undo(self):
                    self.scene.removeItem(self.node)
                    
                def redo(self):
                    if self.node not in self.scene.items():
                        self.scene.addItem(self.node)
                    
            self.undo_stack.push(AddNodeCommand(self.scene(), node))
            return node
            
        return None
        
    def dragEnterEvent(self, event):
        """Handle drag enter events for node creation"""
        if event.mimeData().hasFormat("application/x-node"):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)
            
    def dragMoveEvent(self, event):
        """Handle drag move events for node creation"""
        if event.mimeData().hasFormat("application/x-node"):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)
            
    def dropEvent(self, event):
        """Handle drop events for node creation"""
        if event.mimeData().hasFormat("application/x-node"):
            data = event.mimeData().data("application/x-node")
            stream = QDataStream(data, QIODevice.ReadOnly)
            node_id = stream.readQString()
            
            # Get position in scene coordinates
            pos = self.mapToScene(event.pos())
            
            # Create the node
            self.create_node(node_id, pos)
            
            event.acceptProposedAction()
        else:
            super().dropEvent(event)
            
    def wheelEvent(self, event):
        """Handle wheel events for zooming"""
        zoom_in = event.angleDelta().y() > 0
        
        if zoom_in:
            self.scale(self.scale_factor, self.scale_factor)
        else:
            self.scale(1.0 / self.scale_factor, 1.0 / self.scale_factor)
            
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Delete:
            # Delete selected items
            self.delete_selected_items()
        elif event.matches(QKeySequence.Cut):
            # Cut operation - copy then delete
            if self.copy_selected_nodes():
                self.delete_selected_items()
        elif event.matches(QKeySequence.Copy):
            self.copy_selected_nodes()
        elif event.matches(QKeySequence.Paste):
            self.paste_nodes()
        else:
            super().keyPressEvent(event)

    def delete_selected_items(self):
        """Delete the selected items in the scene"""
        selected_items = self.scene().selectedItems()
        if not selected_items:
            return
            
        # Create a simplified undo command
        class DeleteItemsCommand(QUndoCommand):
            def __init__(self, scene, items):
                super().__init__("Delete Items")
                self.scene = scene
                self.items = items
                # Store the items for restoration
                self.stored_items = []
                
                # Collect all nodes and connected wires
                for item in items:
                    if isinstance(item, Node):
                        # For nodes, also delete connected wires
                        connected_wires = []
                        for socket in item.input_sockets + item.output_sockets:
                            connected_wires.extend(socket.wires)
                        self.stored_items.append((item, connected_wires))
                    elif isinstance(item, Wire):
                        self.stored_items.append((item, []))
                    else:
                        self.stored_items.append((item, []))
                
            def undo(self):
                # Restore all items
                for item, connected_items in self.stored_items:
                    try:
                        if item.scene() != self.scene:
                            self.scene.addItem(item)
                    except:
                        try:
                            self.scene.addItem(item)
                        except:
                            pass
                            
                    # Restore connected items
                    for connected_item in connected_items:
                        try:
                            if connected_item.scene() != self.scene:
                                self.scene.addItem(connected_item)
                        except:
                            try:
                                self.scene.addItem(connected_item)
                            except:
                                pass
                                
            def redo(self):
                # Remove all items
                for item, _ in self.stored_items:
                    try:
                        if item.scene() == self.scene:
                            self.scene.removeItem(item)
                    except:
                        # Just ignore errors when removing items
                        pass
        
        # Add command to undo stack
        self.undo_stack.push(DeleteItemsCommand(self.scene(), selected_items))
        
        # Actually delete the items
        for item in selected_items:
            if isinstance(item, Node):
                # For nodes, also delete connected wires
                for socket in item.input_sockets + item.output_sockets:
                    for wire in list(socket.wires):  # Create a copy of the list
                        wire.remove()
                try:
                    self.scene().removeItem(item)
                except:
                    pass
            elif isinstance(item, Wire):
                # For wires, remove them properly
                item.remove()
            else:
                try:
                    self.scene().removeItem(item)
                except:
                    pass
        
    def serialize_scene(self):
        """Serialize the scene to JSON format"""
        nodes_data = []
        connections_data = []
        
        # Collect all nodes
        for item in self.scene().items():
            if isinstance(item, Node):
                node_data = {
                    "id": id(item),
                    "type": item.__class__.__name__,
                    "x": item.x(),
                    "y": item.y()
                }
                
                # Add node-specific data
                if isinstance(item, InputNode):
                    node_data["value"] = item.value
                
                nodes_data.append(node_data)
                
                # Collect all connections from this node
                for socket in item.output_sockets:
                    for wire in socket.wires:
                        if wire.source_socket and wire.target_socket:
                            connection_data = {
                                "start_node": id(wire.source_socket.parent_node),
                                "start_socket": item.output_sockets.index(wire.source_socket),
                                "end_node": id(wire.target_socket.parent_node),
                                "end_socket": wire.target_socket.parent_node.input_sockets.index(wire.target_socket)
                            }
                            connections_data.append(connection_data)
                            
        return {
            "nodes": nodes_data,
            "connections": connections_data
        }
        
    def deserialize_scene(self, data):
        """Deserialize the scene from JSON format"""
        # Clear the scene
        self.scene().clear()
        
        # Map of node IDs to actual node objects
        nodes = {}
        
        # Create all nodes
        for node_data in data["nodes"]:
            node_type = node_data["type"]
            pos = QPointF(node_data["x"], node_data["y"])
            
            # Create the node based on its type
            if node_type == "InputNode":
                node = InputNode(self.scene())
                if "value" in node_data:
                    node.value = node_data["value"]
                    node.updateLogic()
            elif node_type == "OutputNode":
                node = OutputNode(self.scene())
            elif node_type == "AndGateNode":
                node = AndGateNode(self.scene())
            elif node_type == "OrGateNode":
                node = OrGateNode(self.scene())
            elif node_type == "NotGateNode":
                node = NotGateNode(self.scene())
            elif node_type == "NandGateNode":
                node = NandGateNode(self.scene())
            elif node_type == "NorGateNode":
                node = NorGateNode(self.scene())
            elif node_type == "XorGateNode":
                node = XorGateNode(self.scene())
            elif node_type == "XnorGateNode":
                node = XnorGateNode(self.scene())
            else:
                continue
                
            node.setPos(pos)
            self.scene().addItem(node)
            nodes[node_data["id"]] = node
            
        # Create all connections
        for connection_data in data["connections"]:
            if connection_data["start_node"] in nodes and connection_data["end_node"] in nodes:
                start_node = nodes[connection_data["start_node"]]
                end_node = nodes[connection_data["end_node"]]
                
                # Get the sockets
                if (0 <= connection_data["start_socket"] < len(start_node.output_sockets) and
                    0 <= connection_data["end_socket"] < len(end_node.input_sockets)):
                    
                    start_socket = start_node.output_sockets[connection_data["start_socket"]]
                    end_socket = end_node.input_sockets[connection_data["end_socket"]]
                    
                    # Create the wire
                    wire = Wire(start_socket, end_socket)
                    wire.update_position()
                    
                    # Add the wire to the scene
                    self.scene().addItem(wire)

    def copy_selected_nodes(self):
        """Copy currently selected nodes"""
        self.copied_nodes = []
        selected_nodes = []
        selected_node_ids = set()  # Use a set for faster lookups
        
        # First, collect all selected nodes
        for item in self.scene().selectedItems():
            if isinstance(item, Node):
                selected_nodes.append(item)
                node_id = id(item)
                selected_node_ids.add(node_id)
                
                # Store node information for later pasting
                self.copied_nodes.append({
                    "type": item.__class__.__name__,
                    "pos": item.pos(),
                    "id": node_id  # Store the original node ID for connection mapping
                })
        
        # Check if any nodes were selected
        if not selected_nodes:
            self.copied_connections = []
            return False
            
        # Now collect connections between selected nodes
        self.copied_connections = []
        
        # We'll check all wires in the scene and find those connecting selected nodes
        all_wires = []
        for node in selected_nodes:
            # Collect wires from output sockets
            for socket in node.output_sockets:
                all_wires.extend(socket.wires)
            
            # Also check input sockets to be thorough
            for socket in node.input_sockets:
                all_wires.extend(socket.wires)
        
        # Now find connections between selected nodes
        for wire in all_wires:
            # Make sure the wire has both source and target
            if not wire.source_socket or not wire.target_socket:
                continue
                
            source_node = wire.source_socket.parent_node
            target_node = wire.target_socket.parent_node
            
            source_id = id(source_node)
            target_id = id(target_node)
            
            # Only include wires where both source and target nodes are selected
            if source_id in selected_node_ids and target_id in selected_node_ids:
                connection_data = {
                    "start_node_id": source_id,
                    "start_socket_index": source_node.output_sockets.index(wire.source_socket),
                    "end_node_id": target_id,
                    "end_socket_index": target_node.input_sockets.index(wire.target_socket)
                }
                
                # Check if this connection is already in the list (avoid duplicates)
                if connection_data not in self.copied_connections:
                    self.copied_connections.append(connection_data)
        
        # Debug print
        print(f"Copied {len(self.copied_nodes)} nodes and {len(self.copied_connections)} connections")
        for i, connection in enumerate(self.copied_connections):
            src_id = connection["start_node_id"]
            tgt_id = connection["end_node_id"]
            print(f"  Connection {i+1}: ID {src_id} socket {connection['start_socket_index']} -> ID {tgt_id} socket {connection['end_socket_index']}")
        
        return True  # Return True as we successfully copied at least one node
    
    def paste_nodes(self):
        """Paste previously copied nodes"""
        if not self.copied_nodes:
            return False
            
        # Debug print
        print(f"Pasting {len(self.copied_nodes)} nodes and {len(self.copied_connections)} connections")
        if self.copied_connections:
            print("Connections to paste:", self.copied_connections)
        
        # Deselect all items
        for item in self.scene().selectedItems():
            item.setSelected(False)
        
        # Keep track of created nodes and map old IDs to new nodes
        pasted_nodes = []
        id_mapping = {}  # Maps old node IDs to new node objects
        
        # Create a new node for each copied node
        for node_data in self.copied_nodes:
            node_type = node_data["type"]
            pos = node_data["pos"] + QPointF(self.copy_offset, self.copy_offset)
            original_id = node_data["id"]
            
            # Create the node based on its type
            node = None
            if node_type == "InputNode":
                node = InputNode(self.scene())
            elif node_type == "OutputNode":
                node = OutputNode(self.scene())
            elif node_type == "AndGateNode":
                node = AndGateNode(self.scene())
            elif node_type == "OrGateNode":
                node = OrGateNode(self.scene())
            elif node_type == "NotGateNode":
                node = NotGateNode(self.scene())
            elif node_type == "NandGateNode":
                node = NandGateNode(self.scene())
            elif node_type == "NorGateNode":
                node = NorGateNode(self.scene())
            elif node_type == "XorGateNode":
                node = XorGateNode(self.scene())
            elif node_type == "XnorGateNode":
                node = XnorGateNode(self.scene())
            
            if node:
                # Set position and select
                node.setPos(pos)
                self.scene().addItem(node)
                node.setSelected(True)
                pasted_nodes.append(node)
                
                # Store the mapping from original ID to new node
                id_mapping[original_id] = node
                print(f"Created {node_type} node from original ID {original_id}")
        
        # Create connections between pasted nodes
        created_wires = []
        for connection in self.copied_connections:
            print(f"Processing connection: {connection}")
            
            if (connection["start_node_id"] in id_mapping and 
                connection["end_node_id"] in id_mapping):
                
                start_node = id_mapping[connection["start_node_id"]]
                end_node = id_mapping[connection["end_node_id"]]
                
                print(f"Found both nodes in id_mapping: {start_node.__class__.__name__} -> {end_node.__class__.__name__}")
                
                # Check socket indices
                if (0 <= connection["start_socket_index"] < len(start_node.output_sockets) and
                    0 <= connection["end_socket_index"] < len(end_node.input_sockets)):
                    
                    source_socket = start_node.output_sockets[connection["start_socket_index"]]
                    target_socket = end_node.input_sockets[connection["end_socket_index"]]
                    
                    print(f"Creating wire from socket {connection['start_socket_index']} to socket {connection['end_socket_index']}")
                    
                    # Create wire and add to scene
                    wire = Wire(source_socket, target_socket)
                    self.scene().addItem(wire)
                    wire.update_position()
                    created_wires.append(wire)
                    
                    print(f"Wire created and added to scene")
                else:
                    print(f"Socket indices out of range: {connection['start_socket_index']} or {connection['end_socket_index']}")
            else:
                print(f"Node IDs not found in mapping: {connection['start_node_id']} or {connection['end_node_id']}")
                print(f"Available IDs in mapping: {list(id_mapping.keys())}")
        
        # Increment the copy offset for next paste
        self.copy_offset += 20
        
        # Reset offset if it gets too large
        if self.copy_offset > 200:
            self.copy_offset = 20
            
        # Register paste action for undo/redo
        if pasted_nodes:
            class PasteNodesCommand(QUndoCommand):
                def __init__(self, scene, nodes, wires):
                    super().__init__("Paste Nodes")
                    self.scene = scene
                    self.nodes = nodes
                    self.wires = wires
                    
                def undo(self):
                    # First remove all wires
                    for wire in self.wires:
                        try:
                            if wire.scene() == self.scene:
                                wire.remove()
                        except:
                            # Wire might already be removed
                            pass
                    
                    # Then remove all nodes
                    for node in self.nodes:
                        try:
                            if node.scene() == self.scene:
                                self.scene.removeItem(node)
                        except:
                            # Node might be in a different scene or already removed
                            pass
                        
                def redo(self):
                    # Add nodes to scene
                    for node in self.nodes:
                        try:
                            if node.scene() != self.scene:
                                self.scene.addItem(node)
                                node.setSelected(True)
                        except:
                            # Handle any error
                            pass
                    
                    # Wires will be reconnected by the paste operation
                    
            self.undo_stack.push(PasteNodesCommand(self.scene(), pasted_nodes, created_wires))
            
        return len(pasted_nodes) > 0

class NodeEditorTab(QWidget):
    """Tab containing a node editor view"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = None
        self.layout = QVBoxLayout(self)
        
        # Create scene and view
        self.scene = NodeEditorScene()
        self.view = NodeEditorView(self.scene, self)
        self.layout.addWidget(self.view)
        
    def load_from_file(self, file_path):
        """Load the scene from a file"""
        try:
            with open(file_path, 'r') as f:
                scene_data = json.load(f)
                
            # Clear existing scene
            self.scene.clear()
            
            # Load scene data
            self.view.deserialize_scene(scene_data)
            self.file_path = file_path
            return True
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Error loading file: {str(e)}")
            return False
        
    def save_to_file(self, file_path=None):
        """Save the scene to a file"""
        if not file_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save File", "", "Logic Gate Files (*.lgf)")
                
        if file_path:
            if not file_path.endswith('.lgf'):
                file_path += '.lgf'
                
            try:
                scene_data = self.view.serialize_scene()
                with open(file_path, 'w') as f:
                    json.dump(scene_data, f, indent=4)
                self.file_path = file_path
                return True
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Error saving file: {str(e)}")
                
        return False

# Main Application Class
class LogicGateSimulator(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Logic Gate Simulator")
        self.setGeometry(100, 100, 1200, 800)
        
        # Set application theme
        self.theme = "dark"
        self.apply_theme()
        
        # Create central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.layout.addWidget(self.tab_widget)
        
        # Create side panel with node types
        self.setup_node_dock()
        
        # Create toolbars and menus
        self.setup_toolbar()
        self.setup_menu()
        
        # Add initial tab
        self.add_tab()
        
    def setup_node_dock(self):
        """Create the node list dock widget"""
        self.node_dock = QDockWidget("Logic Gate Nodes", self)
        self.node_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # Create node list
        self.node_list = NodeListWidget()
        self.node_dock.setWidget(self.node_list)
        
        # Add dock to main window
        self.addDockWidget(Qt.LeftDockWidgetArea, self.node_dock)
        
    def setup_toolbar(self):
        """Create toolbars"""
        # File toolbar
        self.file_toolbar = QToolBar("File")
        self.addToolBar(self.file_toolbar)
        
        # Add new file action
        new_action = QAction("New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.add_tab)
        self.file_toolbar.addAction(new_action)
        
        # Add open file action
        open_action = QAction("Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        self.file_toolbar.addAction(open_action)
        
        # Add save file action
        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(lambda: self.save_file(False))
        self.file_toolbar.addAction(save_action)
        
        # Add save as file action
        save_as_action = QAction("Save As", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(lambda: self.save_file(True))
        self.file_toolbar.addAction(save_as_action)
        
        # Edit toolbar
        self.edit_toolbar = QToolBar("Edit")
        self.addToolBar(self.edit_toolbar)
        
        # Add edit actions
        self.undo_action = QAction("Undo", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.triggered.connect(self.undo)
        self.edit_toolbar.addAction(self.undo_action)
        
        self.redo_action = QAction("Redo", self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.triggered.connect(self.redo)
        self.edit_toolbar.addAction(self.redo_action)
        
        # Create delete action to be shared between toolbar and menu
        self.delete_action = QAction("Delete", self)
        self.delete_action.setShortcut(QKeySequence.Delete)
        self.delete_action.triggered.connect(self.delete_selected)
        self.edit_toolbar.addAction(self.delete_action)
        
    def setup_menu(self):
        """Create menus"""
        # Create menu bar
        self.menu_bar = self.menuBar()
        
        # File menu
        file_menu = self.menu_bar.addMenu("&File")
        
        # Add actions to file menu
        new_action = QAction("&New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.add_tab)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(lambda: self.save_file(False))
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save &As", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(lambda: self.save_file(True))
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = self.menu_bar.addMenu("&Edit")
        
        # Use shared actions for undo/redo from toolbar
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)
        
        edit_menu.addSeparator()
        
        cut_action = QAction("Cu&t", self)
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(self.cut)
        edit_menu.addAction(cut_action)
        
        copy_action = QAction("&Copy", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.copy)
        edit_menu.addAction(copy_action)
        
        paste_action = QAction("&Paste", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self.paste)
        edit_menu.addAction(paste_action)
        
        edit_menu.addSeparator()
        
        # Use the shared delete action instead of creating a new one
        edit_menu.addAction(self.delete_action)
        
        # Window menu
        window_menu = self.menu_bar.addMenu("&Window")
        
        theme_menu = window_menu.addMenu("&Theme")
        
        light_theme_action = QAction("&Light", self)
        light_theme_action.triggered.connect(lambda: self.change_theme("light"))
        theme_menu.addAction(light_theme_action)
        
        dark_theme_action = QAction("&Dark", self)
        dark_theme_action.triggered.connect(lambda: self.change_theme("dark"))
        theme_menu.addAction(dark_theme_action)
        
        custom_theme_action = QAction("&Custom...", self)
        custom_theme_action.triggered.connect(self.choose_custom_theme)
        theme_menu.addAction(custom_theme_action)
        
    def add_tab(self):
        """Add a new tab with a node editor"""
        tab = NodeEditorTab(self)
        index = self.tab_widget.addTab(tab, "Untitled")
        self.tab_widget.setCurrentIndex(index)
        
    def close_tab(self, index):
        """Close the tab at the given index"""
        tab = self.tab_widget.widget(index)
        
        # Check if there are unsaved changes
        if tab.file_path is None:
            reply = QMessageBox.question(
                self, "Close Tab", "This tab has not been saved. Do you want to save it?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Save:
                if not tab.save_to_file():
                    # User cancelled save dialog
                    return
            elif reply == QMessageBox.Cancel:
                # User cancelled closing
                return
        
        # Remove the tab
        self.tab_widget.removeTab(index)
        
        # If no tabs remain, create a new one
        if self.tab_widget.count() == 0:
            self.add_tab()
            
    def current_tab(self):
        """Get the currently active tab"""
        return self.tab_widget.currentWidget()
        
    def open_file(self):
        """Open a file from disk"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "Logic Gate Files (*.lgf)")
            
        if file_path:
            # Check if the file is already open
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                if tab.file_path == file_path:
                    self.tab_widget.setCurrentIndex(i)
                    return
                    
            # Create a new tab and load the file
            tab = NodeEditorTab(self)
            if tab.load_from_file(file_path):
                # Add the tab with the file name as title
                file_name = os.path.basename(file_path)
                index = self.tab_widget.addTab(tab, file_name)
                self.tab_widget.setCurrentIndex(index)
            
    def save_file(self, save_as=False):
        """Save the current tab to a file"""
        tab = self.current_tab()
        if not tab:
            return
            
        file_path = tab.file_path
        if save_as or not file_path:
            file_path = None  # Force a Save As dialog
            
        if tab.save_to_file(file_path):
            # Update tab title
            file_name = os.path.basename(tab.file_path)
            index = self.tab_widget.currentIndex()
            self.tab_widget.setTabText(index, file_name)
            
    def delete_selected(self):
        """Delete selected items in the current tab"""
        tab = self.current_tab()
        if tab:
            # Simulate pressing the delete key
            event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier)
            tab.view.keyPressEvent(event)
            
    def undo(self):
        """Undo the last action"""
        tab = self.current_tab()
        if tab and tab.view:
            tab.view.undo_stack.undo()
            
    def redo(self):
        """Redo the last undone action"""
        tab = self.current_tab()
        if tab and tab.view:
            tab.view.undo_stack.redo()
            
    def cut(self):
        """Cut selected items"""
        tab = self.current_tab()
        if tab and tab.view:
            # First copy
            if tab.view.copy_selected_nodes():
                # Then delete
                self.delete_selected()
            
    def copy(self):
        """Copy selected items"""
        tab = self.current_tab()
        if tab and tab.view:
            success = tab.view.copy_selected_nodes()
            if success:
                print("Copied nodes to clipboard")
            
    def paste(self):
        """Paste copied items"""
        tab = self.current_tab()
        if tab and tab.view:
            success = tab.view.paste_nodes()
            if success:
                print("Pasted nodes from clipboard")
    
    def change_theme(self, theme):
        """Change the application theme"""
        self.theme = theme
        self.apply_theme()
        
    def choose_custom_theme(self):
        """Let the user choose a custom color for the theme"""
        color = QColorDialog.getColor(QColor(40, 40, 40), self, "Choose Background Color")
        if color.isValid():
            self.theme = "custom"
            self.theme_color = color
            self.apply_theme()
            
    def apply_theme(self):
        """Apply the current theme to the application"""
        if self.theme == "dark":
            # Dark theme
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2D2D30;
                    color: #FFFFFF;
                }
                QTabWidget {
                    background-color: #2D2D30;
                    color: #FFFFFF;
                }
                QTabWidget::pane {
                    border: 1px solid #3F3F46;
                    background-color: #2D2D30;
                }
                QTabBar::tab {
                    background-color: #252526;
                    color: #FFFFFF;
                    padding: 5px;
                    border: 1px solid #3F3F46;
                }
                QTabBar::tab:selected {
                    background-color: #3F3F46;
                }
                QDockWidget {
                    background-color: #252526;
                    color: #FFFFFF;
                    border: 1px solid #3F3F46;
                }
                QDockWidget::title {
                    background-color: #3F3F46;
                    padding: 5px;
                }
                QListWidget {
                    background-color: #252526;
                    color: #FFFFFF;
                    border: 1px solid #3F3F46;
                }
                QListWidget::item:selected {
                    background-color: #3F3F46;
                }
                QMenuBar {
                    background-color: #2D2D30;
                    color: #FFFFFF;
                }
                QMenuBar::item:selected {
                    background-color: #3F3F46;
                }
                QMenu {
                    background-color: #2D2D30;
                    color: #FFFFFF;
                    border: 1px solid #3F3F46;
                }
                QMenu::item:selected {
                    background-color: #3F3F46;
                }
                QToolBar {
                    background-color: #2D2D30;
                    border: 1px solid #3F3F46;
                }
            """)
        elif self.theme == "light":
            # Light theme
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #F0F0F0;
                    color: #000000;
                }
                QTabWidget {
                    background-color: #F0F0F0;
                    color: #000000;
                }
                QTabWidget::pane {
                    border: 1px solid #C0C0C0;
                    background-color: #F0F0F0;
                }
                QTabBar::tab {
                    background-color: #E0E0E0;
                    color: #000000;
                    padding: 5px;
                    border: 1px solid #C0C0C0;
                }
                QTabBar::tab:selected {
                    background-color: #F0F0F0;
                }
                QDockWidget {
                    background-color: #F0F0F0;
                    color: #000000;
                    border: 1px solid #C0C0C0;
                }
                QDockWidget::title {
                    background-color: #E0E0E0;
                    padding: 5px;
                }
                QListWidget {
                    background-color: #FFFFFF;
                    color: #000000;
                    border: 1px solid #C0C0C0;
                }
                QListWidget::item:selected {
                    background-color: #C0C0C0;
                }
                QMenuBar {
                    background-color: #F0F0F0;
                    color: #000000;
                }
                QMenuBar::item:selected {
                    background-color: #E0E0E0;
                }
                QMenu {
                    background-color: #F0F0F0;
                    color: #000000;
                    border: 1px solid #C0C0C0;
                }
                QMenu::item:selected {
                    background-color: #E0E0E0;
                }
                QToolBar {
                    background-color: #F0F0F0;
                    border: 1px solid #C0C0C0;
                }
            """)
        elif self.theme == "custom" and hasattr(self, 'theme_color'):
            # Custom theme based on user-selected color
            bg_color = self.theme_color.name()
            text_color = "#FFFFFF" if self.theme_color.lightness() < 128 else "#000000"
            
            # Create a darker and lighter shade for various UI elements
            darker_color = QColor(self.theme_color).darker(120).name()
            lighter_color = QColor(self.theme_color).lighter(120).name()
            
            self.setStyleSheet(f"""
                QMainWindow {{
                    background-color: {bg_color};
                    color: {text_color};
                }}
                QTabWidget {{
                    background-color: {bg_color};
                    color: {text_color};
                }}
                QTabWidget::pane {{
                    border: 1px solid {lighter_color};
                    background-color: {bg_color};
                }}
                QTabBar::tab {{
                    background-color: {darker_color};
                    color: {text_color};
                    padding: 5px;
                    border: 1px solid {lighter_color};
                }}
                QTabBar::tab:selected {{
                    background-color: {bg_color};
                }}
                QDockWidget {{
                    background-color: {darker_color};
                    color: {text_color};
                    border: 1px solid {lighter_color};
                }}
                QDockWidget::title {{
                    background-color: {darker_color};
                    padding: 5px;
                }}
                QListWidget {{
                    background-color: {darker_color};
                    color: {text_color};
                    border: 1px solid {lighter_color};
                }}
                QListWidget::item:selected {{
                    background-color: {lighter_color};
                }}
                QMenuBar {{
                    background-color: {bg_color};
                    color: {text_color};
                }}
                QMenuBar::item:selected {{
                    background-color: {lighter_color};
                }}
                QMenu {{
                    background-color: {bg_color};
                    color: {text_color};
                    border: 1px solid {lighter_color};
                }}
                QMenu::item:selected {{
                    background-color: {lighter_color};
                }}
                QToolBar {{
                    background-color: {bg_color};
                    border: 1px solid {lighter_color};
                }}
            """)
            
            # Also update the scene background color
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                if tab and hasattr(tab, 'view') and hasattr(tab.view, 'scene'):
                    tab.view.scene().setBackgroundBrush(QBrush(self.theme_color))
        
    def closeEvent(self, event):
        """Handle application close event"""
        # Check for unsaved changes in all tabs
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if tab.file_path is None:
                reply = QMessageBox.question(
                    self,
                    "Unsaved Changes",
                    f"Tab {i+1} has not been saved. Do you want to save it?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
                )
                
                if reply == QMessageBox.Save:
                    self.tab_widget.setCurrentIndex(i)
                    if not tab.save_to_file():
                        # User cancelled save dialog
                        event.ignore()
                        return
                elif reply == QMessageBox.Cancel:
                    # User cancelled closing
                    event.ignore()
                    return
                    
        # Accept the event to close the application
        event.accept()

# Main entry point
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LogicGateSimulator()
    window.show()
    sys.exit(app.exec_()) 