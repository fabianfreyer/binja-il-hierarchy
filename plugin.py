import typing

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from pathlib import Path

from PySide6.QtWidgets import QVBoxLayout, QLabel, QWidget, QSizePolicy

from binaryninjaui import (
    DisassemblyContainer,
    Sidebar,
    SidebarWidget,
    SidebarWidgetType,
    FlowGraphWidget,
    View,
)

from binaryninja import (
    BinaryView,
    Function,
    FlowGraph,
)

from binaryninja.enums import FunctionGraphType

root = Path(__file__).parent

class HierarchyGraph(FlowGraphWidget):
    def __init__(self, parent: QWidget, view: BinaryView, graph) -> None:
        FlowGraphWidget.__init__(self, parent, view, None)


class HierarchyWindow(SidebarWidget):
    supported_view_types = [
        FunctionGraphType.LiftedILFunctionGraph,
        FunctionGraphType.LowLevelILFunctionGraph,
        FunctionGraphType.MediumLevelILFunctionGraph,
        FunctionGraphType.HighLevelILFunctionGraph,
        FunctionGraphType.LowLevelILSSAFormFunctionGraph,
        FunctionGraphType.MediumLevelILSSAFormFunctionGraph,
        FunctionGraphType.HighLevelILSSAFormFunctionGraph,
    ]

    def __init__(self, name, _frame, bv: typing.Optional[BinaryView] = None):
        SidebarWidget.__init__(self, name)

        self._function = None
        self._bv = None
        self._il_index = None
        self._offset = None
        self._view_type = None

        # Configures configured_arch, _bv, and arch_explainer
        self._layout = QVBoxLayout(self)
        self._layout.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)

        self._hidden = QLabel()
        self._hidden.setText("No IL instruction selected")
        self._hidden.setWordWrap(True)
        self._layout.addWidget(self._hidden)

        self._graph = HierarchyGraph(self, bv, None)
        self._graph.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._graph.hide()
        self._layout.addWidget(self._graph)

        self.update_needed = False
        self.bv = bv
        self.function = None
        self.view_widget = None

    def update(self):
        if not self.update_needed:
            return

        graph = self.current_il_hierarchy
        if graph:
            self._graph.show()
            self._hidden.hide()
            self._graph.setGraph(self.current_il_hierarchy)
        else:
            self._graph.hide()
            self._hidden.show()

        self.update_needed = False

    @property
    def bv(self) -> typing.Optional[BinaryView]:
        return self._bv

    @bv.setter
    def bv(self, new_bv: typing.Optional[BinaryView]):
        self._bv = new_bv

    @property
    def offset(self) -> typing.Optional[int]:
        return self._offset

    @property
    def view_widget(self) -> typing.Optional[View]:
        return self._view_widget

    @view_widget.setter
    def view_widget(self, value):
        if isinstance(value, DisassemblyContainer):
            value = value.getView()
        if not isinstance(value, View):
            value = None
        self._view_widget = value

        if not value:
            self.view_type = None
            self.il_index = None
            self.function = None
        else:
            self.view_type = self._view_widget.getILViewType()
            self.il_index = self._view_widget.getCurrentILInstructionIndex()
            self.function = self._view_widget.getCurrentFunction()

    @property
    def current_il(self):
        if any([
            self.il_index is None,
            self.function is None,
            self.bv is None,
            self.view_type not in self.supported_view_types,
        ]):
            return None

        try:
            if self.view_type == FunctionGraphType.LiftedILFunctionGraph:
                return self.function.lifted_il[self.il_index]
            if self.view_type == FunctionGraphType.LowLevelILFunctionGraph:
                return self.function.llil[self.il_index]
            if self.view_type == FunctionGraphType.MediumLevelILFunctionGraph:
                return self.function.mlil[self.il_index]
            if self.view_type == FunctionGraphType.HighLevelILFunctionGraph:
                return self.function.hlil[self.il_index]
            if self.view_type == FunctionGraphType.LowLevelILSSAFormFunctionGraph:
                return self.function.llil.ssa_form[self.il_index]
            if self.view_type == FunctionGraphType.MediumLevelILSSAFormFunctionGraph:
                return self.function.mlil.ssa_form[self.il_index]
            if self.view_type == FunctionGraphType.HighLevelILSSAFormFunctionGraph:
                return self.function.hlil.ssa_form[self.il_index]
        except IndexError:
            return None

    @property
    def current_il_hierarchy(self) -> typing.Optional[FlowGraph]:
        if not self.current_il:
            return None
        return self.current_il.add_subgraph(FlowGraph(), {})

    @property
    def view_type(self) -> FunctionGraphType:
        return self._view_type

    @view_type.setter
    def view_type(self, value: FunctionGraphType):
        if self._view_type != value:
            self.update_needed = True
        self._view_type = value
        self.update()

    @property
    def il_index(self) -> typing.Optional[int]:
        return self._il_index

    @il_index.setter
    def il_index(self, value: typing.Optional[int]):
        if value == 0xffff_ffff_ffff_ffff:
            value = None
        if self._il_index != value:
            self.update_needed = True
        self._il_index = value
        self.update()

    @property
    def function(self) -> typing.Optional[Function]:
        return self._function

    @function.setter
    def function(self, value: typing.Optional[Function]):
        if self._function != value:
            self.update_needed = True
        self._function = value
        self.update()

    def offset(self, offset: typing.Optional[int]):
        self._offset = offset

    def notifyOffsetChanged(self, offset):
        self.offset = offset

    def notifyViewChanged(self, view_frame):
        if view_frame is None:
            self.bv = None
            self.view_widget = None
        else:
            self.view_widget = view_frame.getCurrentWidget()
            view = view_frame.getCurrentViewInterface()
            self.bv = view.getData()


class HierarchySidebarWidgetType(SidebarWidgetType):
    def __init__(self):
        # Icon is Hierarchy by Bieu Tuong from NounProject.com
        # https://thenounproject.com/icon/hierarchy-4512362/
        icon = QImage(str(root.joinpath("icon.png")))
        SidebarWidgetType.__init__(self, icon, "IL Hierarchy")

    def createWidget(self, frame, data):
        # This callback is called when a widget needs to be created for a given context. Different
        # widgets are created for each unique BinaryView. They are created on demand when the sidebar
        # widget is visible and the BinaryView becomes active.
        return HierarchyWindow("IL Hierarchy", frame, data)

Sidebar.addSidebarWidgetType(HierarchySidebarWidgetType())