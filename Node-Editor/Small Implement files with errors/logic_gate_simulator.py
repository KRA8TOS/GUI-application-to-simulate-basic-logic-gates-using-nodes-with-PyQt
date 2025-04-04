import sys
import os
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QAction, QMenu, QToolBar, 
                             QLabel, QLineEdit, QPushButton, QFileDialog, 
                             QComboBox, QGraphicsView, QGraphicsScene, 
                             QGraphicsItem, QGraphicsEllipseItem, QGraphicsLineItem,
                             QGraphicsTextItem, QDockWidget, QListWidget, 
                             QListWidgetItem, QMessageBox)
from PyQt5.QtCore import Qt, QPointF, QRectF, QLineF, pyqtSignal, QMimeData, QObject
from PyQt5.QtGui import QColor, QPen, QBrush, QFont, QDrag, QPixmap, QPainter


class Wire(QGraphicsLineItem):
    """Represents a connection wire between nodes"""
    def __init__(self, source_socket, target_socket, parent=None):
        super().__init__(parent)
        self.source_socket = source_socket
        self.target_socket = target_socket
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setPen(QPen(QColor(200, 200, 200), 2))
        self.update_position()
        
    def update_position(self):
        try:
            if self.source_socket and self.target_socket:
                source_pos = self.source_socket.scenePos() + QPointF(5, 5)
                target_pos = self.target_socket.scenePos() + QPointF(5, 5)
                self.setLine(QLineF(source_pos, target_pos))
        except Exception as e:
            print(f"Error in Wire.update_position: {str(e)}")
            
    def remove(self):
        try:
            if self.source_socket and self in self.source_socket.connections:
                self.source_socket.connections.remove(self)
            if self.target_socket and self in self.target_socket.connections:
                self.target_socket.connections.remove(self)
            if self.scene():
                self.scene().removeItem(self)
        except Exception as e:
            print(f"Error in Wire.remove: {str(e)}")


class Socket(QObject, QGraphicsEllipseItem):
    """Represents an input or output socket for a node"""
    def __init__(self, node, socket_type, index=0, parent=None):
        QObject.__init__(self, parent)
        QGraphicsEllipseItem.__init__(self, parent)
        self.node = node
        self.socket_type = socket_type  # 'input' or 'output'
        self.index = index
        self.connections = []
        self.value = False
        
        # Set appearance
        self.setRect(0, 0, 10, 10)
        self.setBrush(QBrush(QColor(0, 0, 0)))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        
        # Temporary line for dragging
        self.temp_line = None
        
    def __del__(self):
        # Clean up connections
        if hasattr(self, 'connections'):
            for wire in list(self.connections):
                if wire and wire.scene():
                    wire.remove()
            self.connections.clear()
        
    def remove(self):
        # Remove all connections
        for wire in list(self.connections):
            if wire and wire.scene():
                wire.remove()
        self.connections.clear()
        
        # Remove from scene
        if self.scene():
            try:
                self.scene().removeItem(self)
            except:
                print("Error removing socket from scene")
        
    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(QColor(100, 100, 255)))
        super().hoverEnterEvent(event)
        
    def hoverLeaveEvent(self, event):
        self.setBrush(QBrush(QColor(0, 0, 0)))
        super().hoverLeaveEvent(event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Start drawing a line
            if self.socket_type == 'output':
                scene_pos = self.scenePos() + QPointF(5, 5)
                self.temp_line = QGraphicsLineItem(QLineF(scene_pos, scene_pos))
                self.temp_line.setPen(QPen(QColor(200, 200, 200), 2))
                self.scene().addItem(self.temp_line)
                event.accept()
            super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        if self.temp_line and self.socket_type == 'output':
            try:
                # Update the line to follow the mouse
                start_pos = self.scenePos() + QPointF(5, 5)
                end_pos = start_pos + event.scenePos() - event.buttonDownScenePos(Qt.LeftButton)
                self.temp_line.setLine(QLineF(start_pos, end_pos))
                event.accept()
            except Exception as e:
                print(f"Error in mouseMoveEvent: {str(e)}")
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        if self.temp_line and self.socket_type == 'output':
            try:
                scene = self.scene()
                if not scene:
                    return
                
                end_pos = self.scenePos() + event.scenePos() - event.buttonDownScenePos(Qt.LeftButton)
                
                # Check if we're over an input socket
                items = scene.items(end_pos)
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
                                self.node.output_value_changed.emit()
                                break
                
                # Remove temporary line
                if self.temp_line and self.temp_line.scene():
                    scene.removeItem(self.temp_line)
                    self.temp_line = None
                
                event.accept()
            except Exception as e:
                print(f"Error in mouseReleaseEvent: {str(e)}")
                if self.temp_line and self.temp_line.scene():
                    try:
                        self.scene().removeItem(self.temp_line)
                    except:
                        pass
                self.temp_line = None
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


class Node(QObject, QGraphicsItem):
    """Base class for all logic gate nodes"""
    output_value_changed = pyqtSignal()
    
    def __init__(self, scene, title, inputs=0, outputs=1, width=150, height=100):
        QObject.__init__(self)
        QGraphicsItem.__init__(self)
        self.editor_scene = scene
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
        
    def __del__(self):
        # Clean up sockets
        try:
            for socket in list(self.input_sockets) + list(self.output_sockets):
                socket.remove()
            self.input_sockets.clear()
            self.output_sockets.clear()
        except:
            print("Error in Node.__del__")
        
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
        try:
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
        except Exception as e:
            print(f"Error in Node.paint: {str(e)}")
                         
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            try:
                # Update wires when node is moved
                for socket in self.input_sockets + self.output_sockets:
                    for wire in socket.connections:
                        wire.update_position()
            except Exception as e:
                print(f"Error in itemChange: {str(e)}")
        return super().itemChange(change, value)
        
    def get_output_value(self):
        # Should be implemented by subclasses
        return False
        
    def perform_logic(self):
        # Should be implemented by subclasses
        pass
        
    def remove(self):
        try:
            # Remove all connected wires first
            for socket in list(self.input_sockets) + list(self.output_sockets):
                for wire in list(socket.connections):  # Make a copy to avoid modification during iteration
                    if wire and wire.scene():
                        wire.remove()
            
            # Remove from scene
            if self.scene():
                self.scene().removeItem(self)
        except Exception as e:
            print(f"Error in Node.remove: {str(e)}")


class InputNode(Node):
    """Node that allows manual input of a boolean value"""
    def __init__(self, scene):
        super().__init__(scene, "Input", 0, 1)
        
        # Set value
        self.value = False
        
        # Create text item for the value display
        self.text_item = QGraphicsTextItem(self)
        self.text_item.setPos(10, 40)
        self.text_item.setPlainText("Value: 0")
        self.text_item.setDefaultTextColor(QColor(255, 255, 255))
        
        # Update output socket visual
        if self.output_sockets:
            self.output_sockets[0].set_value(self.value)
        
    def paint(self, painter, option, widget):
        try:
            super().paint(painter, option, widget)
            
            # Draw toggle button
            painter.setBrush(QColor(100, 100, 100))
            painter.setPen(QPen(QColor(150, 150, 150), 1))
            painter.drawRoundedRect(self.width/2 - 30, 60, 60, 25, 5, 5)
            
            # Draw button text
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(QRectF(self.width/2 - 30, 60, 60, 25),
                         Qt.AlignCenter, "Toggle")
        except Exception as e:
            print(f"Error painting InputNode: {str(e)}")
        
    def mouseDoubleClickEvent(self, event):
        try:
            # Check if click is within toggle button area
            if (self.width/2 - 30 <= event.pos().x() <= self.width/2 + 30 and 
                60 <= event.pos().y() <= 85):
                # Toggle value on double-click
                self.value = not self.value
                self.text_item.setPlainText(f"Value: {1 if self.value else 0}")
                
                # Update output socket visual
                if self.output_sockets:
                    self.output_sockets[0].set_value(self.value)
                    
                # Signal value change to connected nodes
                self.output_value_changed.emit()
            super().mouseDoubleClickEvent(event)
        except Exception as e:
            print(f"Error in InputNode.mouseDoubleClickEvent: {str(e)}")
            super().mouseDoubleClickEvent(event)
        
    def get_output_value(self):
        return self.value


class OutputNode(Node):
    """Node that displays the output value"""
    def __init__(self, scene, write_to_file=False):
        super().__init__(scene, "Output" if not write_to_file else "Write Output", 1, 0)
        self.write_to_file = write_to_file
        self.value = False
        
        if write_to_file:
            # Create text item for the button
            button_text = QGraphicsTextItem("Save to File", self)
            button_text.setPos(30, 40)
            button_text.setDefaultTextColor(QColor(255, 255, 255))
            
    def paint(self, painter, option, widget):
        try:
            super().paint(painter, option, widget)
            
            # Draw node-specific elements
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(QRectF(10, 40, self.width - 20, 20),
                          Qt.AlignLeft, f"Value: {1 if self.get_output_value() else 0}")
                          
            if self.write_to_file:
                # Draw a button-like rectangle
                painter.setBrush(QColor(100, 100, 100))
                painter.setPen(QPen(QColor(150, 150, 150), 1))
                painter.drawRoundedRect(30, 60, self.width - 60, 30, 5, 5)
                
                # Draw button text
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(QRectF(30, 60, self.width - 60, 30),
                              Qt.AlignCenter, "Save to File")
        except Exception as e:
            print(f"Error painting OutputNode: {str(e)}")
        
    def mouseDoubleClickEvent(self, event):
        try:
            if self.write_to_file:
                # Check if click is within button area
                if 30 <= event.pos().x() <= self.width - 30 and 60 <= event.pos().y() <= 90:
                    self.save_to_file()
        except Exception as e:
            print(f"Error in OutputNode.mouseDoubleClickEvent: {str(e)}")
        super().mouseDoubleClickEvent(event)
        
    def save_to_file(self):
        try:
            value = self.get_output_value()
            file_path, _ = QFileDialog.getSaveFileName(None, "Save Output", "", "Text Files (*.txt)")
            if file_path:
                with open(file_path, 'w') as f:
                    f.write(f"Output Value: {1 if value else 0}")
                QMessageBox.information(None, "Success", f"Output value saved to {file_path}")
        except Exception as e:
            print(f"Error saving to file: {str(e)}")
            QMessageBox.critical(None, "Error", f"Failed to save: {str(e)}")
            
    def get_output_value(self):
        try:
            if self.input_sockets and self.input_sockets[0].connections:
                return self.input_sockets[0].get_value()
        except Exception as e:
            print(f"Error getting output value: {str(e)}")
        return False


class LogicGateNode(Node):
    """Base class for all logic gate nodes"""
    def __init__(self, scene, title, inputs=2, outputs=1):
        super().__init__(scene, title, inputs, outputs)
        
    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        
        # Draw truth table or symbol
        input_values = [socket.get_value() for socket in self.input_sockets]
        output_value = self.get_output_value()
        
        painter.setPen(QColor(255, 255, 255))
        y_pos = self.title_height + 20
        
        for i, value in enumerate(input_values):
            painter.drawText(QRectF(10, y_pos, self.width - 20, 20),
                           Qt.AlignLeft, f"In {i+1}: {1 if value else 0}")
            y_pos += 20
            
        painter.drawText(QRectF(10, y_pos, self.width - 20, 20),
                       Qt.AlignLeft, f"Out: {1 if output_value else 0}")
        
    def get_output_value(self):
        # Get all input values
        input_values = []
        for socket in self.input_sockets:
            input_values.append(socket.get_value())
            
        # Perform logic (implemented by subclasses)
        result = self.perform_logic(input_values)
        
        # Update output socket visual
        if self.output_sockets:
            self.output_sockets[0].set_value(result)
            
        return result


class AndGateNode(LogicGateNode):
    def __init__(self, scene):
        super().__init__(scene, "AND Gate")
        
    def perform_logic(self, inputs):
        if len(inputs) < 2:
            return False
        return inputs[0] and inputs[1]


class OrGateNode(LogicGateNode):
    def __init__(self, scene):
        super().__init__(scene, "OR Gate")
        
    def perform_logic(self, inputs):
        if len(inputs) < 2:
            return False
        return inputs[0] or inputs[1]


class NotGateNode(LogicGateNode):
    def __init__(self, scene):
        super().__init__(scene, "NOT Gate", 1)
        
    def perform_logic(self, inputs):
        if not inputs:
            return True  # NOT of no input is True
        return not inputs[0]


class NandGateNode(LogicGateNode):
    def __init__(self, scene):
        super().__init__(scene, "NAND Gate")
        
    def perform_logic(self, inputs):
        if len(inputs) < 2:
            return True
        return not (inputs[0] and inputs[1])


class NorGateNode(LogicGateNode):
    def __init__(self, scene):
        super().__init__(scene, "NOR Gate")
        
    def perform_logic(self, inputs):
        if len(inputs) < 2:
            return True
        return not (inputs[0] or inputs[1])


class XorGateNode(LogicGateNode):
    def __init__(self, scene):
        super().__init__(scene, "XOR Gate")
        
    def perform_logic(self, inputs):
        if len(inputs) < 2:
            return False
        return inputs[0] != inputs[1]


class XnorGateNode(LogicGateNode):
    def __init__(self, scene):
        super().__init__(scene, "XNOR Gate")
        
    def perform_logic(self, inputs):
        if len(inputs) < 2:
            return True
        return inputs[0] == inputs[1]


class NodeListWidget(QListWidget):
    """Widget that displays available node types and allows drag & drop"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        
        # Add node types
        node_types = [
            ("Input", "Input Node"),
            ("Output", "Output Node"),
            ("Write Output", "Write Output Node"),
            ("Read Input", "Read From File Node"),
            ("4-bit Output", "4-bit Output Node"),
            ("8-bit Output", "8-bit Output Node"),
            ("AND", "AND Gate"),
            ("OR", "OR Gate"),
            ("NOT", "NOT Gate"),
            ("NAND", "NAND Gate"),
            ("NOR", "NOR Gate"),
            ("XOR", "XOR Gate"),
            ("XNOR", "XNOR Gate"),
        ]
        
        for node_id, node_name in node_types:
            item = QListWidgetItem(node_name)
            item.setData(Qt.UserRole, node_id)
            self.addItem(item)
    
    def startDrag(self, supported_actions):
        print("NodeListWidget.startDrag")
        item = self.currentItem()
        if item:
            node_id = item.data(Qt.UserRole)
            print(f"Starting drag with node_id: {node_id}")
            
            # Create mime data
            mime_data = QMimeData()
            mime_data.setText(node_id)
            
            # Create drag object
            drag = QDrag(self)
            drag.setMimeData(mime_data)
            
            # Create a simple pixmap for the drag icon
            pixmap = QPixmap(100, 50)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setPen(QPen(QColor(200, 200, 200), 1))
            painter.setBrush(QBrush(QColor(60, 60, 60)))
            painter.drawRoundedRect(0, 0, 100, 50, 10, 10)
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, item.text())
            painter.end()
            
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPointF(pixmap.width()/2, pixmap.height()/2).toPoint())
            
            # Execute drag
            print("Executing drag")
            result = drag.exec_(Qt.CopyAction)
            print(f"Drag result: {result}")


class NodeEditorScene(QGraphicsScene):
    """Custom scene for the node editor"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, 5000, 5000)
        self.setBackgroundBrush(QBrush(QColor(40, 40, 40)))


class NodeEditorView(QGraphicsView):
    """Custom view for the node editor"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setRenderHint(QPainter.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        # Create scene
        self.scene = NodeEditorScene(self)
        self.setScene(self.scene)
        
    def dragEnterEvent(self, event):
        print("NodeEditorView.dragEnterEvent")
        if event.mimeData().hasText():
            print(f"Drag data: {event.mimeData().text()}")
            event.accept()
        else:
            event.ignore()
            
    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.accept()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        print("NodeEditorView.dropEvent")
        if event.mimeData().hasText():
            try:
                # Get node ID from mime data
                node_id = event.mimeData().text()
                print(f"Dropping node_id: {node_id}")
                
                # Convert view coordinates to scene coordinates
                pos = self.mapToScene(event.pos())
                print(f"Pos: {pos.x()}, {pos.y()}")
                
                # Create the appropriate node
                print(f"Creating node of type: {node_id}")
                node = self.create_node(node_id)
                if node:
                    print("Node created successfully")
                    node.setPos(pos)
                    print("Node position set")
                    self.scene.addItem(node)
                    print("Node added to scene")
                    event.accept()
                    return
                else:
                    print(f"Failed to create node of type {node_id}")
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"Error in dropEvent: {str(e)}")
                
        event.ignore()
        
    def wheelEvent(self, event):
        # Zoom in/out with mouse wheel
        zoom_factor = 1.15
        
        if event.angleDelta().y() > 0:
            # Zoom in
            self.scale(zoom_factor, zoom_factor)
        else:
            # Zoom out
            self.scale(1.0 / zoom_factor, 1.0 / zoom_factor)
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            # Delete selected items
            for item in self.scene.selectedItems():
                if isinstance(item, Node):
                    item.remove()
                elif isinstance(item, Wire):
                    item.remove()
        super().keyPressEvent(event)
            
    def create_node(self, node_id):
        """Create a node based on the node ID"""
        try:
            if node_id == "Input":
                return InputNode(self.scene)
            elif node_id == "Output":
                return OutputNode(self.scene)
            elif node_id == "Write Output":
                return OutputNode(self.scene, write_to_file=True)
            elif node_id == "Read Input":
                return ReadFromFileNode(self.scene)
            elif node_id == "4-bit Output":
                return MultibitOutputNode(self.scene, 4)
            elif node_id == "8-bit Output":
                return MultibitOutputNode(self.scene, 8)
            elif node_id == "AND":
                return AndGateNode(self.scene)
            elif node_id == "OR":
                return OrGateNode(self.scene)
            elif node_id == "NOT":
                return NotGateNode(self.scene)
            elif node_id == "NAND":
                return NandGateNode(self.scene)
            elif node_id == "NOR":
                return NorGateNode(self.scene)
            elif node_id == "XOR":
                return XorGateNode(self.scene)
            elif node_id == "XNOR":
                return XnorGateNode(self.scene)
            
            print(f"Unknown node type: {node_id}")
            return None
        except Exception as e:
            print(f"Error creating node {node_id}: {str(e)}")
            return None

    def serialize_scene(self):
        """Save scene data to a dictionary"""
        data = {
            'nodes': [],
            'connections': []
        }
        
        # Save nodes
        for item in self.scene.items():
            if isinstance(item, Node):
                node_data = {
                    'id': id(item),
                    'type': item.__class__.__name__,
                    'x': item.x(),
                    'y': item.y()
                }
                
                # Save additional properties for specific node types
                if isinstance(item, InputNode):
                    node_data['value'] = item.value
                    
                data['nodes'].append(node_data)
                
        # Save connections
        for item in self.scene.items():
            if isinstance(item, Wire):
                # Find the nodes that own these sockets
                source_node = item.source_socket.node
                target_node = item.target_socket.node
                
                connection_data = {
                    'source_node': id(source_node),
                    'source_socket': item.source_socket.index,
                    'target_node': id(target_node),
                    'target_socket': item.target_socket.index
                }
                data['connections'].append(connection_data)
                
        return data
        
    def deserialize_scene(self, data):
        """Load scene from saved data"""
        # Clear existing scene
        self.scene.clear()
        
        # Map of saved node IDs to actual node objects
        node_map = {}
        
        # Create nodes
        for node_data in data['nodes']:
            node_type = node_data['type']
            pos_x = node_data['x']
            pos_y = node_data['y']
            
            # Create the appropriate node
            node = None
            
            if node_type == 'InputNode':
                node = InputNode(self.scene)
                if 'value' in node_data:
                    node.value = node_data['value']
                    node.update_value(str(1 if node.value else 0))
            elif node_type == 'OutputNode':
                node = OutputNode(self.scene, False)
            elif node_type == 'WriteOutputNode':
                node = OutputNode(self.scene, True)
            elif node_type == 'AndGateNode':
                node = AndGateNode(self.scene)
            elif node_type == 'OrGateNode':
                node = OrGateNode(self.scene)
            elif node_type == 'NotGateNode':
                node = NotGateNode(self.scene)
            elif node_type == 'NandGateNode':
                node = NandGateNode(self.scene)
            elif node_type == 'NorGateNode':
                node = NorGateNode(self.scene)
            elif node_type == 'XorGateNode':
                node = XorGateNode(self.scene)
            elif node_type == 'XnorGateNode':
                node = XnorGateNode(self.scene)
            
            if node:
                node.setPos(pos_x, pos_y)
                self.scene.addItem(node)
                node_map[node_data['id']] = node
        
        # Create connections
        for conn_data in data['connections']:
            source_node_id = conn_data['source_node']
            source_socket_idx = conn_data['source_socket']
            target_node_id = conn_data['target_node']
            target_socket_idx = conn_data['target_socket']
            
            if source_node_id in node_map and target_node_id in node_map:
                source_node = node_map[source_node_id]
                target_node = node_map[target_node_id]
                
                if (source_socket_idx < len(source_node.output_sockets) and 
                    target_socket_idx < len(target_node.input_sockets)):
                    
                    source_socket = source_node.output_sockets[source_socket_idx]
                    target_socket = target_node.input_sockets[target_socket_idx]
                    
                    wire = Wire(source_socket, target_socket)
                    self.scene.addItem(wire)
                    source_socket.connections.append(wire)
                    target_socket.connections.append(wire)
    
    def closeEvent(self, event):
        # Clean up scene
        self.scene.clear()
        super().closeEvent(event)


class NodeEditorTab(QWidget):
    """Tab containing a node editor view"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = None
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create view
        self.view = NodeEditorView(self)
        layout.addWidget(self.view)
        
    def save_to_file(self, file_path=None):
        if not file_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save As", "", "Logic Gate Files (*.lgf)")
                
        if file_path:
            data = self.view.serialize_scene()
            with open(file_path, 'w') as f:
                json.dump(data, f)
            self.file_path = file_path
            return True
        return False
        
    def load_from_file(self, file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            self.view.deserialize_scene(data)
            self.file_path = file_path
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")
            return False


class LogicGateSimulator(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Logic Gate Simulator")
        self.setGeometry(100, 100, 1200, 800)
        
        
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
        
        # Add delete action
        delete_action = QAction("Delete", self)
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(self.delete_selected)
        self.edit_toolbar.addAction(delete_action)
        
        # Add run simulation action
        run_action = QAction("Run Simulation", self)
        run_action.setShortcut("F5")
        run_action.triggered.connect(self.run_simulation)
        self.edit_toolbar.addAction(run_action)
        
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
        
        delete_action = QAction("&Delete", self)
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(self.delete_selected)
        edit_menu.addAction(delete_action)
        
        # View menu
        view_menu = self.menu_bar.addMenu("&View")
        
        # Toggle dock visibility
        toggle_dock_action = QAction("Node &Panel", self)
        toggle_dock_action.setCheckable(True)
        toggle_dock_action.setChecked(True)
        toggle_dock_action.triggered.connect(lambda checked: self.node_dock.setVisible(checked))
        view_menu.addAction(toggle_dock_action)
        
        # Simulation menu
        sim_menu = self.menu_bar.addMenu("&Simulation")
        
        run_action = QAction("&Run", self)
        run_action.setShortcut("F5")
        run_action.triggered.connect(self.run_simulation)
        sim_menu.addAction(run_action)
        
        # Help menu
        help_menu = self.menu_bar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
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
            
    def run_simulation(self):
        """Execute the simulation"""
        tab = self.current_tab()
        if tab:
            # Update all nodes in the scene by triggering signal connections
            for item in tab.view.scene.items():
                if isinstance(item, InputNode):
                    item.output_value_changed.emit()
            
            # Refresh the view
            tab.view.viewport().update()
            
    def show_about(self):
        """Show the about dialog"""
        QMessageBox.about(
            self,
            "About Logic Gate Simulator",
            "Logic Gate Simulator\n\n"
            "A visual programming tool for creating and simulating digital logic circuits.\n\n"
            "Usage:\n"
            "1. Drag nodes from the left panel to the workspace\n"
            "2. Connect nodes by dragging from output sockets to input sockets\n"
            "3. Double-click on Input nodes to toggle their values\n"
            "4. Run the simulation to see the results\n\n"
            "© 2025 Logic Gate Simulator Team"
        )
        
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


class ReadFromFileNode(Node):
    """Node that reads boolean values from a file"""
    def __init__(self, scene):
        super().__init__(scene, "Read Input", 0, 1)
        self.file_path = None
        self.value = False
        
        # Create load button text
        button_text = QGraphicsTextItem("Load File", self)
        button_text.setPos(30, 70)
        button_text.setDefaultTextColor(QColor(255, 255, 255))
        
    def paint(self, painter, option, widget):
        try:
            super().paint(painter, option, widget)
            
            # Draw node-specific elements
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(QRectF(10, 40, self.width - 20, 20),
                         Qt.AlignLeft, f"Value: {1 if self.value else 0}")
            
            # Draw file path if any
            if self.file_path:
                file_name = os.path.basename(self.file_path)
                painter.drawText(QRectF(10, 60, self.width - 20, 20),
                             Qt.AlignLeft, f"File: {file_name}")
            
            # Draw a button-like rectangle
            painter.setBrush(QColor(100, 100, 100))
            painter.setPen(QPen(QColor(150, 150, 150), 1))
            painter.drawRoundedRect(30, 90, self.width - 60, 30, 5, 5)
            
            # Draw button text
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(QRectF(30, 90, self.width - 60, 30),
                          Qt.AlignCenter, "Load File")
        except Exception as e:
            print(f"Error painting ReadFromFileNode: {str(e)}")
    
    def mouseDoubleClickEvent(self, event):
        try:
            # Check if click is within button area
            if 30 <= event.pos().x() <= self.width - 30 and 90 <= event.pos().y() <= 120:
                self.load_from_file()
        except Exception as e:
            print(f"Error in ReadFromFileNode.mouseDoubleClickEvent: {str(e)}")
        super().mouseDoubleClickEvent(event)
    
    def load_from_file(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(None, "Load Input", "", "Text Files (*.txt)")
            if file_path:
                with open(file_path, 'r') as f:
                    content = f.read().strip()
                
                # Try to parse the content as a boolean value
                if content.lower() in ('1', 'true', 'yes', 'on'):
                    self.value = True
                else:
                    self.value = False
                
                self.file_path = file_path
                
                # Update output socket visual
                if self.output_sockets:
                    self.output_sockets[0].set_value(self.value)
                
                # Signal value change to connected nodes
                self.output_value_changed.emit()
                
                return True
        except Exception as e:
            print(f"Error loading from file: {str(e)}")
            QMessageBox.critical(None, "Error", f"Failed to load input: {str(e)}")
        
        return False
    
    def get_output_value(self):
        return self.value


class MultibitOutputNode(Node):
    """Node that displays multiple bits of output"""
    def __init__(self, scene, num_inputs=4):
        super().__init__(scene, f"{num_inputs}-bit Output", num_inputs, 0, width=180)
        self.values = [False] * num_inputs
    
    def paint(self, painter, option, widget):
        try:
            super().paint(painter, option, widget)
            
            # Draw node-specific elements
            y_pos = self.title_height + 20
            
            # Draw each input bit
            for i in range(len(self.input_sockets)):
                value = self.input_sockets[i].get_value()
                self.values[i] = value
                
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(QRectF(10, y_pos, self.width - 20, 20),
                             Qt.AlignLeft, f"Bit {i}: {1 if value else 0}")
                y_pos += 20
            
            # Draw the decimal value
            decimal_value = 0
            for i, bit in enumerate(reversed(self.values)):
                if bit:
                    decimal_value += (1 << i)
            
            painter.setPen(QColor(200, 200, 100))
            painter.drawText(QRectF(10, y_pos, self.width - 20, 20),
                         Qt.AlignLeft, f"Decimal: {decimal_value}")
        except Exception as e:
            print(f"Error painting MultibitOutputNode: {str(e)}")
    
    def get_output_value(self):
        # This node is output-only, but we implement this for consistency
        return False


# Add main function to start the application
if __name__ == "__main__":
    # Enable exception handling
    import sys
    
    def exception_hook(exctype, value, traceback):
        print('Exception hook called')
        print(repr(exctype))
        print(repr(value))
        print(repr(traceback))
        sys.__excepthook__(exctype, value, traceback)
    
    sys.excepthook = exception_hook
    
    app = QApplication(sys.argv)
    window = LogicGateSimulator()
    window.show()
    sys.exit(app.exec_())