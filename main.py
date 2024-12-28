import math
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.scatter import Scatter
from kivy.uix.widget import Widget
from kivy.graphics import Line, Ellipse, Color, Rectangle
from kivy.core.window import Window
from kivy.core.text import Label as CoreLabel

class HaversinePolygonApp(App):
    def build(self):
        self.coords = []
        self.redo_stack = []

        # Set background color to white
        Window.clearcolor = (1, 1, 1, 1)

        # Main layout
        self.layout = BoxLayout(orientation='vertical', padding=50, spacing=5)

        # Input fields
        self.lat_input = TextInput(
            hint_text='North', multiline=False, font_size=50, size_hint_y=None, height=70
        )
        self.lat_input.bind(on_text_validate=self.focus_lon_input)

        self.lon_input = TextInput(
            hint_text='East', multiline=False, font_size=50, size_hint_y=None, height=70
        )
        self.lon_input.bind(on_text_validate=self.add_point)

        # Scale input field
        self.scale_input = TextInput(
            hint_text='Scale (e.g., 100000)', multiline=False, font_size=50, size_hint_y=None, height=70, text='100000'
        )
        self.scale_input.bind(text=lambda instance, value: self.update_polygon_sketch())

        # Buttons
        add_coord_button = Button(
            text='Add Point', font_size=50, size_hint_y=None, height=70, background_color=(0.2, 0.6, 0.8, .8)
        )
        add_coord_button.bind(on_press=self.add_point)

        calc_area_button = Button(
            text='Calculate Area', font_size=50, size_hint_y=None, height=70, background_color=(0.2, 0.6, 0.8, .8)
        )
        calc_area_button.bind(on_press=self.calculate_area)

        clear_button = Button(
            text='Clear Points', font_size=50, size_hint_y=None, height=70, background_color=(2, 0.5, 0, 1)
        )
        clear_button.bind(on_press=self.clear_points)

        undo_button = Button(
            text='Undo', font_size=50, size_hint_y=None, height=70, background_color=(2, .8, .5, 3)
        )
        undo_button.bind(on_press=self.undo_last_point)

        redo_button = Button(
            text='Redo', font_size=50, size_hint_y=None, height=70, background_color=(0, 2, 0, 1)
        )
        redo_button.bind(on_press=self.redo_last_action)

        # Points display (scrollable)
        self.points_display = ScrollView(size_hint=(1, None), height=200)
        self.points_box = BoxLayout(orientation='vertical', size_hint_y=None)
        self.points_box.bind(minimum_height=self.points_box.setter('height'))
        self.points_display.add_widget(self.points_box)

        # Add background color to points display
        with self.points_display.canvas.before:
            Color(0.2, 0.2, 0.2, .2)  # Light gray
            self.points_display.bg_rect = Rectangle(size=self.points_display.size, pos=self.points_display.pos)
        self.points_display.bind(size=self.update_scrollview_bg, pos=self.update_scrollview_bg)

        # Distances display (scrollable)
        self.distances_display = ScrollView(size_hint=(1, None), height=200)
        self.distances_box = BoxLayout(orientation='vertical', size_hint_y=None)
        self.distances_box.bind(minimum_height=self.distances_box.setter('height'))
        self.distances_display.add_widget(self.distances_box)

        # Add background color to distances display
        with self.distances_display.canvas.before:
            Color(0.2, 0.2, .2, .2)  # Light blue
            self.distances_display.bg_rect = Rectangle(size=self.distances_display.size, pos=self.distances_display.pos)
        self.distances_display.bind(size=self.update_scrollview_bg, pos=self.update_scrollview_bg)

        # Area output
        self.area_output = Label(
            text='', size_hint_y=None, height=150, font_size=45, color=(0, 0, 0, 1),
            halign='center', valign='middle'
        )
        self.area_output.bind(size=self.area_output.setter('text_size'))

        # Sketch container
        self.sketch_container = Scatter(
            do_scale=True, do_translation=True, do_rotation=False, size_hint=(1, None), height=200
        )
        self.sketch = Widget()
        self.sketch_container.add_widget(self.sketch)

        # Adding widgets to layout
        self.layout.add_widget(self.lat_input)
        self.layout.add_widget(self.lon_input)
        self.layout.add_widget(self.scale_input)
        self.layout.add_widget(add_coord_button)
        self.layout.add_widget(calc_area_button)
        self.layout.add_widget(clear_button)
        undo_redo_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=70)
        undo_redo_layout.add_widget(undo_button)
        undo_redo_layout.add_widget(redo_button)
        self.layout.add_widget(undo_redo_layout)
        self.layout.add_widget(self.points_display)
        self.layout.add_widget(self.distances_display)
        self.layout.add_widget(self.area_output)
        self.layout.add_widget(self.sketch_container)

        return self.layout

    def update_scrollview_bg(self, instance, value):
        """Update the background rectangle of the scrollviews."""
        if hasattr(instance, 'bg_rect'):
            instance.bg_rect.size = instance.size
            instance.bg_rect.pos = instance.pos

    def focus_lon_input(self, instance):
        """Move focus from North to East when Enter is pressed."""
        self.lon_input.focus = True

    def add_point(self, instance=None):
        """Add a new point."""
        try:
            lat = float(self.lat_input.text)
            lon = float(self.lon_input.text)
            self.coords.append((lat, lon))
            self.redo_stack.clear()
            self.update_points_display()
            self.update_distances_display()
            self.update_polygon_sketch()
            self.lat_input.text = ''
            self.lon_input.text = ''
            self.lat_input.focus = True
        except ValueError:
            self.area_output.text = "Invalid input. Please enter numeric values."

    def undo_last_point(self, instance):
        """Undo the last added point."""
        if self.coords:
            last_point = self.coords.pop()
            self.redo_stack.append(last_point)
            self.update_points_display()
            self.update_distances_display()
            self.update_polygon_sketch()

    def redo_last_action(self, instance):
        """Redo the last undone action."""
        if self.redo_stack:
            last_undone_point = self.redo_stack.pop()
            self.coords.append(last_undone_point)
            self.update_points_display()
            self.update_distances_display()
            self.update_polygon_sketch()

    def update_points_display(self):
        """Update the list of points displayed in the ScrollView."""
        self.points_box.clear_widgets()
        for index, (lat, lon) in enumerate(self.coords):
            point_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
            label = Label(
                text=f"{index + 1}: ({lat:.6f}, {lon:.6f})", size_hint_y=None, height=50, font_size=40, color=(0, 0, 0, 1)
            )
            edit_button = Button(
                text='Edit', size_hint=(None, None), size=(100, 45.0), font_size=40, background_color=(0.6, 0.8, 5, 1)
            )
            edit_button.bind(on_press=lambda btn, idx=index: self.edit_point(idx))
            point_layout.add_widget(label)
            point_layout.add_widget(edit_button)
            self.points_box.add_widget(point_layout)

    def edit_point(self, index):
        """Edit a specific point."""
        try:
            lat, lon = self.coords[index]
            self.lat_input.text = str(lat)
            self.lon_input.text = str(lon)
            del self.coords[index]
            self.update_points_display()
            self.update_distances_display()
            self.update_polygon_sketch()
        except IndexError:
            self.area_output.text = "Error: Unable to edit the point."

    def update_distances_display(self):
        """Update the distances between consecutive points."""
        self.distances_box.clear_widgets()
        if len(self.coords) < 2:
            return

        for i in range(1, len(self.coords)):
            lat1, lon1 = self.coords[i - 1]
            lat2, lon2 = self.coords[i]
            distance = self.haversine_distance(lat1, lon1, lat2, lon2)
            label = Label(
                text=f"Distance {i}: {distance:.2f} m", size_hint_y=None, height=50, font_size=40, color=(0, 0, 0, 1)
            )
            self.distances_box.add_widget(label)

        # Add distance between the first and last point only after the third point is entered
        if len(self.coords) >= 3:
            lat1, lon1 = self.coords[-1]
            lat2, lon2 = self.coords[0]
            distance = self.haversine_distance(lat1, lon1, lat2, lon2)
            label = Label(
                text=f"Distance {len(self.coords)}: {distance:.2f} m", size_hint_y=None, height=50, font_size=40, color=(0, 0, 0, 1)
            )
            self.distances_box.add_widget(label)

    def update_polygon_sketch(self):
        """Draw a centered sketch of the polygon with numbered points."""
        self.sketch.canvas.clear()
        if len(self.coords) < 1 or self.sketch.width == 0 or self.sketch.height == 0:
            return

        min_lat = min(lat for lat, _ in self.coords)
        min_lon = min(lon for _, lon in self.coords)
        max_lat = max(lat for lat, _ in self.coords)
        max_lon = max(lon for _, lon in self.coords)

        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2

        try:
            scale = float(self.scale_input.text)
        except ValueError:
            scale = 100000

        offset_x = self.sketch.width / 2
        offset_y = self.sketch.height / 2

        with self.sketch.canvas:
            Color(0, 0, 1, 1)
            points = [
                ((lon - center_lon) * scale + offset_x, (lat - center_lat) * scale + offset_y)
                for lat, lon in self.coords
            ]
            if len(points) > 1:
                Line(points=[coord for point in points for coord in point], width=6, close=True)

            for i, (x, y) in enumerate(points):
                Color(1, 0, 0, 1)
                Ellipse(pos=(x - 5, y - 5), size=(10, 10))
                Color(0, 0, 0, 1)
                label = CoreLabel(text=str(i + 1), font_size=40)
                label.refresh()
                text_texture = label.texture
                Rectangle(texture=text_texture, size=text_texture.size, pos=(x + 10, y + 10))

    def calculate_area(self, instance=None):
        """Calculate and display the area of the polygon."""
        if len(self.coords) < 3:
            self.area_output.text = "Not enough points to form a polygon."
            return

        area_m2 = self.calculate_polygon_area(self.coords)
        feddan = int(area_m2 // 4200)
        remaining_area = area_m2 % 4200
        kirat = int(remaining_area // (4200 / 24))
        saham = round((remaining_area % (4200 / 24)) / (4200 / 24 / 24), 2)
        self.area_output.text = (
            f"Area: {area_m2:.2f} m²\n"
            f"{feddan} F , {kirat} K , {saham:.2f} S "
        )

    def clear_points(self, instance):
        """Clear all points and reset the display."""
        self.coords.clear()
        self.redo_stack.clear()
        self.points_box.clear_widgets()
        self.distances_box.clear_widgets()
        self.sketch.canvas.clear()
        self.area_output.text = "Points cleared."

    def calculate_polygon_area(self, coords):
        """Calculate the area of a polygon using Haversine formula."""
        area = 0
        for i in range(len(coords)):
            j = (i + 1) % len(coords)
            lat1, lon1 = coords[i]
            lat2, lon2 = coords[j]
            area += math.radians(lon2 - lon1) * (2 + math.sin(math.radians(lat1)) + math.sin(math.radians(lat2)))

        area = abs(area * 6378137 ** 2 / 2.0)
        return area

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate the Haversine distance between two points on the Earth."""
        R = 6371000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c


if __name__ == "__main__":
    HaversinePolygonApp().run()
