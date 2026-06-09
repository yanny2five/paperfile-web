import tkinter as tk
from tkinter import ttk


def create_label(parent, text, relx, rely, height=38, width=499, font="-family {Microsoft YaHei UI} -size 16",
                 background="#a6caf0", **kwargs):
    """
    Create and place a Label widget.

    :param parent: The parent widget
    :param text: The text to display on the label
    :param relx: Relative x position (0.0 to 1.0)
    :param rely: Relative y position (0.0 to 1.0)
    :param height: Height of the label
    :param width: Width of the label
    :param font: Font of the label
    :param background: Background color of the label
    :param kwargs: Additional configuration options
    :return: The created Label widget
    """
    label = tk.Label(parent)
    label.place(relx=relx, rely=rely, height=height, width=width)
    label.configure(activebackground=background)
    label.configure(activeforeground="black")
    label.configure(background=background)
    label.configure(compound='left')
    label.configure(disabledforeground="#a3a3a3")
    label.configure(foreground="#000000")
    label.configure(highlightbackground="#d9d9d9")
    label.configure(highlightcolor="#000000")
    label.configure(text=text)
    label.configure(font=font)
    for key, value in kwargs.items():
        label.configure(**{key: value})
    return label


def create_button(parent, text, relx, rely, command, height=50, width=400, font="-family {Microsoft YaHei UI} -size 16",
                  background="#d9d9d9", **kwargs):
    """
    Create and place a Button widget.

    :param parent: The parent widget
    :param text: The text to display on the button
    :param relx: Relative x position (0.0 to 1.0)
    :param rely: Relative y position (0.0 to 1.0)
    :param command: The function to call when the button is clicked
    :param height: Height of the button
    :param width: Width of the button
    :param font: Font of the button
    :param background: Background color of the button
    :param kwargs: Additional configuration options
    :return: The created Button widget
    """
    button = tk.Button(parent)
    button.place(relx=relx, rely=rely, height=height, width=width)
    button.configure(activebackground="#66a3e6")
    button.configure(activeforeground="black")
    button.configure(background=background)
    button.configure(disabledforeground="#a3a3a3")
    button.configure(font=font)
    button.configure(foreground="#000000")
    button.configure(highlightbackground="#808080")
    button.configure(highlightcolor="#000000")
    button.configure(text=text)
    button.configure(command=command)
    for key, value in kwargs.items():
        button.configure(**{key: value})
    return button


def create_checkbutton(parent, text, relx, rely, variable, height=20, width=100, font="-family {Microsoft YaHei UI} -size 12",
                       background="#a6caf0", **kwargs):
    """
    Create and place a Checkbutton widget.

    :param parent: The parent widget
    :param text: The text to display on the checkbutton
    :param relx: Relative x position (0.0 to 1.0)
    :param rely: Relative y position (0.0 to 1.0)
    :param variable: The variable linked to the checkbutton's state
    :param height: Height of the checkbutton
    :param width: Width of the checkbutton
    :param font: Font of the checkbutton
    :param background: Background color of the checkbutton
    :param kwargs: Additional configuration options
    :return: The created Checkbutton widget
    """
    checkbutton = tk.Checkbutton(parent)
    checkbutton.place(relx=relx, rely=rely, height=height, width=width)
    checkbutton.configure(text=text)
    checkbutton.configure(variable=variable)
    checkbutton.configure(font=font)
    checkbutton.configure(background=background)
    for key, value in kwargs.items():
        checkbutton.configure(**{key: value})
    return checkbutton


def create_entry(parent, textvariable, relx, rely, height=30, width=100, font="-family {Microsoft YaHei UI} -size 14",
                 background="white", **kwargs):
    """
    Create and place an Entry widget.

    :param parent: The parent widget
    :param textvariable: The variable linked to the entry's content
    :param relx: Relative x position (0.0 to 1.0)
    :param rely: Relative y position (0.0 to 1.0)
    :param height: Height of the entry
    :param width: Width of the entry
    :param font: Font of the entry
    :param background: Background color of the entry
    :param kwargs: Additional configuration options
    :return: The created Entry widget
    """
    entry = tk.Entry(parent)
    entry.place(relx=relx, rely=rely, height=height, width=width)
    entry.configure(font=font)
    entry.configure(background=background)
    entry.configure(textvariable=textvariable)
    for key, value in kwargs.items():
        entry.configure(**{key: value})
    return entry


def create_radiobutton(parent, text, relx, rely, variable, value, height=20, width=100, font="-family {Microsoft YaHei UI} -size 12",
                       background="#a6caf0", **kwargs):
    """
    Create and place a Radiobutton widget.

    :param parent: The parent widget
    :param text: The text to display on the radiobutton
    :param relx: Relative x position (0.0 to 1.0)
    :param rely: Relative y position (0.0 to 1.0)
    :param variable: The variable linked to the radiobutton's state
    :param value: The value to assign to the variable when the radiobutton is selected
    :param height: Height of the radiobutton
    :param width: Width of the radiobutton
    :param font: Font of the radiobutton
    :param background: Background color of the radiobutton
    :param kwargs: Additional configuration options
    :return: The created Radiobutton widget
    """
    radiobutton = tk.Radiobutton(parent)
    radiobutton.place(relx=relx, rely=rely, height=height, width=width)
    radiobutton.configure(text=text)
    radiobutton.configure(variable=variable)
    radiobutton.configure(value=value)
    radiobutton.configure(font=font)
    radiobutton.configure(background=background)
    for key, value in kwargs.items():
        radiobutton.configure(**{key: value})
    return radiobutton


def create_currentfile_message(parent, file_path, num_entries):
    """
    Create a label to display the current database file path and number of entries.

    :param parent: The parent widget
    :param file_path: Path to the database file
    :param num_entries: Number of entries in the database
    :return: The created label widget
    """
    # Create a label to display the file path and number of entries
    message = f"Current file: {file_path} | Total entries: {num_entries}"
    label = tk.Label(
        parent,
        text=message,
        font="-family {Microsoft YaHei UI} -size 10",
        background="#a6caf0",
        anchor="w"
    )
    label.place(relx=0.007, rely=0.98, relwidth=0.9, height=20)
    return label  # Return the label widget


def create_text(parent, relx, rely, height, width, font="-family {Microsoft YaHei UI} -size 12", background="white", **kwargs):
    """
    Create and place a Text widget with automatic word wrap.

    :param parent: The parent widget
    :param relx: Relative x position (0.0 to 1.0)
    :param rely: Relative y position (0.0 to 1.0)
    :param height: Height of the text widget
    :param width: Width of the text widget
    :param font: Font of the text widget
    :param background: Background color of the text widget
    :param kwargs: Additional configuration options
    :return: The created Text widget
    """
    text = tk.Text(parent)
    text.place(relx=relx, rely=rely, height=height, width=width)
    text.configure(font=font)
    text.configure(background=background)
    text.configure(wrap=tk.WORD)  # Enable word wrap
    for key, value in kwargs.items():
        text.configure(**{key: value})
    return text