"""Regression test: is_element_visible_according_to_all_parents must not mutate node bounds.

The visibility check is meant to be a pure predicate. It used to alias
`node.snapshot_node.bounds` (a mutable DOMRect) as `current_bounds` and then adjust it
in place while walking parent iframe/HTML frames, permanently corrupting the stored
bounds for every later consumer (serializer, paint-order filtering, absolute_position).
"""

from web_agent.dom.service import DomService
from web_agent.dom.views import DOMRect, EnhancedDOMTreeNode, EnhancedSnapshotNode, NodeType


def make_node(node_name: str = 'DIV', bounds: DOMRect | None = None) -> EnhancedDOMTreeNode:
	snapshot_node = None
	if bounds is not None:
		snapshot_node = EnhancedSnapshotNode(
			is_clickable=None,
			cursor_style=None,
			bounds=bounds,
			clientRects=None,
			scrollRects=None,
			computed_styles={},
			paint_order=None,
			stacking_contexts=None,
		)
	return EnhancedDOMTreeNode(
		node_id=1,
		backend_node_id=1,
		node_type=NodeType.ELEMENT_NODE,
		node_name=node_name,
		node_value='',
		attributes={},
		is_scrollable=None,
		is_visible=None,
		absolute_position=None,
		target_id='target-1',  # type: ignore[arg-type]
		frame_id=None,
		session_id=None,
		content_document=None,
		shadow_root_type=None,
		shadow_roots=None,
		parent_node=None,
		children_nodes=None,
		ax_node=None,
		snapshot_node=snapshot_node,
	)


def test_visibility_check_does_not_mutate_element_bounds():
	element_bounds = DOMRect(x=10, y=10, width=50, height=20)
	element = make_node('DIV', bounds=element_bounds)

	iframe_bounds = DOMRect(x=100, y=200, width=800, height=600)
	iframe_frame = make_node('IFRAME', bounds=iframe_bounds)

	DomService.is_element_visible_according_to_all_parents(element, html_frames=[iframe_frame])

	assert element.snapshot_node.bounds.x == 10, 'element bounds.x must be unchanged after a visibility check'
	assert element.snapshot_node.bounds.y == 10, 'element bounds.y must be unchanged after a visibility check'


def test_visibility_check_is_idempotent_across_repeated_calls():
	"""Calling the visibility check twice on the same node must return the same result."""
	element_bounds = DOMRect(x=10, y=10, width=50, height=20)
	element = make_node('DIV', bounds=element_bounds)

	iframe_bounds = DOMRect(x=100, y=200, width=800, height=600)
	iframe_frame = make_node('IFRAME', bounds=iframe_bounds)

	first = DomService.is_element_visible_according_to_all_parents(element, html_frames=[iframe_frame])
	second = DomService.is_element_visible_according_to_all_parents(element, html_frames=[iframe_frame])

	assert first == second
