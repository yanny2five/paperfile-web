import tkinter as tk


class UpdatePage:
    def __init__(self, root):
        """
        Initialize the UpdatePage class.

        :param root: The root window
        """
        self.root = root
        self.current_frame = None
        self.current_search_method = "number"  # Default search method
        self.reader = None

    def clear_widgets(self):
        """
        Destroys all widgets currently packed in the main frame.
        """
        for widget in self.root.winfo_children():
            widget.destroy()

    def set_search_method(self, method):
        """
        Set the current search method.

        :param method: The current search method (e.g., "number", "vitatype")
        """
        self.current_search_method = method

    def show_mainpage(self, reader=None):
        """Open main page and remember the reader."""
        if reader is not None:
            self.reader = reader  # Remember it for later navigations
        from pages.mainpage import start_mainpage
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = start_mainpage(self.root, self, reader=self.reader)
        self.current_frame.pack(fill=tk.BOTH, expand=True)
        if hasattr(self.current_frame, "refresh_file_info"):
            self.current_frame.refresh_file_info()

    def show_retrievepapers_main(self, reader=None, entry_mode="retrieve", edit=False, select_method=None):
        if self.current_frame:
            self.current_frame.destroy()

        from pages.retrievepapers_main import Toplevel1
        self.current_frame = Toplevel1(self.root, reader, entry_mode=entry_mode, edit=edit, select_method=select_method)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_enterpapers(self, reader):
        """
        Show the enterpapers page.

        :param reader: The CNTReader instance
        """
        if self.current_frame:
            self.current_frame.destroy()  # Destroy the current frame

        # Lazy import to avoid circular dependency
        from pages.enterpapers import start_enterpapers
        self.current_frame = start_enterpapers(self.root, reader)  # Pass reader
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_editandfixentries(self, reader):
        """
        Show the enterpapers page.

        :param reader: The CNTReader instance
        """
        if self.current_frame:
            self.current_frame.destroy()  # Destroy the current frame

        # Lazy import to avoid circular dependency
        from pages.editandfixentries import start_editandfixentries
        self.current_frame = start_editandfixentries(self.root, reader)  # Pass reader
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_standardizenames(self, reader):
        """
        Show the enterpapers page.

        :param reader: The CNTReader instance
        """
        if self.current_frame:
            self.current_frame.destroy()  # Destroy the current frame

        # Lazy import to avoid circular dependency
        from pages.standardizename import start_standardizename
        self.current_frame = start_standardizename(self.root, reader)  # Pass reader
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_utilities(self):
        """
        Show the utilities page.
        """
        if self.current_frame:
            self.current_frame.destroy()  # Destroy the current frame

        # Lazy import to avoid circular dependency
        from pages.utilities import start_utilities
        self.current_frame = start_utilities(self.root, self)  # Pass self for navigation
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_generatereports(self, file_path=None):
        """
        Show the generatereports page.

        :param file_path: The path to the database file
        """
        if self.current_frame:
            self.current_frame.destroy()  # Destroy the current frame

        # Lazy import to avoid circular dependency
        from pages.generatereports import start_generatereports
        self.current_frame = start_generatereports(self.root, file_path)  # Pass file_path
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_defineselectedpeople(self, reader=None):
        """
        Show the DefineSelectedPeoplePage.
        """
        if self.current_frame:
            self.current_frame.destroy()  # Destroy the current frame

        # Lazy import to avoid circular dependency
        from pages.defineselectedpeople import start_defineselectedpeople
        self.current_frame = start_defineselectedpeople(self.root, reader=reader)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_publicationtypereport(self, reader, override_names=None, hide_listbox=False):
        if self.current_frame:
            self.current_frame.destroy()
        from pages.publicationtypereport import start_publication_report_page
        self.current_frame = start_publication_report_page(self.root, reader, override_names=override_names,
                                                           hide_listbox=hide_listbox)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_classifyjournals(self, reader=None):
        from pages.classifyjournals import start_classifyjournals_page

        if reader is not None:
            self.reader = reader

        if self.reader is None:
            from tkinter import messagebox
            messagebox.showerror("Error", "No database loaded. Please open a database first.")
            return

        if getattr(self, "current_frame", None):
            try:
                self.current_frame.destroy()
            except Exception:
                pass

        self.current_frame = start_classifyjournals_page(self.root, reader=self.reader)

        if not self.current_frame.winfo_manager():
            import tkinter as tk
            self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_groupoutform(self, params=None):
        if self.current_frame:
            self.current_frame.destroy()
        from pages.groupoutform import start_groupoutform
        if params is None:
            params = {}
        self.current_frame = start_groupoutform(self.root, update_page=self, params=params)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_groupoutput(self, params):
        if self.current_frame:
            self.current_frame.destroy()
        from pages.groupoutput import start_groupoutput
        self.current_frame = start_groupoutput(self.root, params=params, update_page=self)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_compositesummary(self):
        # keep current reader before destroying the frame
        prev_reader = getattr(self.current_frame, "reader", None)
        if self.current_frame:
            self.current_frame.destroy()
        from pages.compositesummary import start_compositesummary_page
        self.current_frame = start_compositesummary_page(self.root, reader=prev_reader,
                                                         update_page=self)  # use keywords
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_specialreportform_1(self, classes=False, journal=False, people=True, label_mode="journal_use_report"):
        if self.current_frame:
            self.current_frame.destroy()
        from pages.specialreportform_1 import start_specialreportform_1
        self.current_frame = start_specialreportform_1(self.root, classes=classes, journal=journal, people=people,
                                                     label_mode=label_mode)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_specialreportform_2(self, classes=False, journal=False, people=True, label_mode="journal_class_report"):
        if self.current_frame:
            self.current_frame.destroy()
        from pages.specialreportform_2 import start_specialreportform_2
        self.current_frame = start_specialreportform_2(self.root, classes=classes, journal=journal, people=people,
                                                     label_mode=label_mode)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_specialreportform_3(self, classes=False, journal=False, people=True, label_mode="journal_use_report"):
        if self.current_frame:
            self.current_frame.destroy()
        from pages.specialreportform_3 import start_specialreportform_3
        self.current_frame = start_specialreportform_3(self.root, classes=classes, journal=journal, people=people,
                                                     label_mode=label_mode)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_checknumbers(self, reader=None):

        if self.current_frame:
            self.current_frame.destroy()

        from pages.checknumbers import start_checknumbers
        self.current_frame = start_checknumbers(self.root, reader=reader, update_page=self)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_duplicate_titles(self, reader=None):
        """Open duplicate titles page; use provided reader or the stored one."""
        from pages.duplicatetitles import start_duplicate_title_page
        # Fallback to the stored reader
        reader = reader or self.reader
        if reader is None:
            messagebox.showerror("Error", "No database loaded. Please open a database first.")
            return
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = start_duplicate_title_page(self.root, reader=reader)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_correctelements(self):
        if self.current_frame:
            self.current_frame.destroy()
        from pages.correctelements import CorrectElementsPage
        self.current_frame = CorrectElementsPage(master=self.root)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_mergedatabase(self):
        if self.current_frame:
            self.current_frame.destroy()
        from pages.mergedatabase import start_mergedatabase_page
        self.current_frame = start_mergedatabase_page(self.root)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_journalnamemapper(self, reader=None, preselect_db_name=None):
        """
        Show the Journal Name Mapper page.
        """
        from pages.journalnamemapper import start_journalnamemapper_page

        if reader is not None:
            self.reader = reader  # Store for later navigation

        if self.reader is None:
            from tkinter import messagebox
            messagebox.showerror("Error", "No database loaded. Please open a database first.")
            return

        # Destroy current frame if exists
        if getattr(self, "current_frame", None):
            try:
                self.current_frame.destroy()
            except Exception:
                pass

        # Load and display the new page
        self.current_frame = start_journalnamemapper_page(self.root, reader=self.reader)

        self.current_frame.preselect_db_name = preselect_db_name  # pass db name to mapper

        if not self.current_frame.winfo_manager():
            import tkinter as tk
            self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_fundingproposalsreport(self, reader=None):
        """
        Show the Funding Proposals Report page.
        """
        if reader is not None:
            self.reader = reader
        if self.current_frame:
            try:
                self.current_frame.destroy()
            except Exception:
                pass
        from pages.fundingproposalsreport import start_fundingproposalsreport
        self.current_frame = start_fundingproposalsreport(self.root, reader=self.reader, update_page=self)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_defaultname(self):
        if self.current_frame:
            try:
                self.current_frame.destroy()
            except Exception:
                pass
        from pages.defaultname import start_defaultname
        self.current_frame = start_defaultname(self.root, update_page=self)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_defaultvitatypes(self):
        if self.current_frame:
            try:
                self.current_frame.destroy()
            except Exception:
                pass
        from pages.defaultvitatypes import start_defaultvitatypes
        self.current_frame = start_defaultvitatypes(self.root, update_page=self)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_chatgpt_api(self):
        if self.current_frame:
            try:
                self.current_frame.destroy()
            except Exception:
                pass
        from pages.chatgpt_api import start_chatgpt_api
        self.current_frame = start_chatgpt_api(self.root, update_page=self)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_journals_people(self, reader=None):
        """
        Show the Journals and People page.

        :param reader: The CNTReader instance
        """
        if reader is not None:
            self.reader = reader

        if self.current_frame:
            try:
                self.current_frame.destroy()
            except Exception:
                pass

        from pages.journalsandpeople import start_journals_people_page
        self.current_frame = start_journals_people_page(self.root, update_page=self, reader=self.reader)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_delete_selected_papers(self):
        """
        Show the Delete Selected Papers page.
        """
        if self.current_frame:
            self.current_frame.destroy()

        # Lazy import to avoid circular dependency
        from pages.delete_selected_papers import start_delete_selected_papers
        self.current_frame = start_delete_selected_papers(self.root, update_page=self)
        self.current_frame.pack(fill=tk.BOTH, expand=True)




