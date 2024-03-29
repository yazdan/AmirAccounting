import pygtk
import gtk
from datetime import date
import os
import platform

from sqlalchemy import or_
from sqlalchemy.orm.util import outerjoin
from sqlalchemy.sql import between, and_
from sqlalchemy.sql.functions import sum

import utility
import printreport
import previewreport
from database import *
from dateentry import *
from amirconfig import config
from helpers import get_builder

class TBalanceReport:
    def __init__(self):
        self.builder = get_builder("report")
        self.window = self.builder.get_object("window3")
        
        self.date = DateEntry()
        box = self.builder.get_object("datebox1")
        box.add(self.date)
        self.date.set_sensitive(False)
        self.date.set_activates_default(True)
        self.date.show()
        
        self.fdate = DateEntry()
        box = self.builder.get_object("fdatebox1")
        box.add(self.fdate)
        self.fdate.set_sensitive(False)
        self.fdate.set_activates_default(True)
        self.fdate.show()
        
        self.tdate = DateEntry()
        box = self.builder.get_object("tdatebox1")
        box.add(self.tdate)
        self.tdate.set_sensitive(False)
        self.tdate.set_activates_default(True)
        self.tdate.show()
        
        self.builder.get_object("allcontent1").set_active(True)
        self.window.show_all()
        self.builder.connect_signals(self)
        
    def createReport(self):
        report_data = []
        remaining = 0
        report_header = [_("Ledger name"), _("Debt"), _("Credit"), _("Remaining")]
        col_width = [31, 23, 23, 23]
        
        query = config.db.session.query(Subject).select_from(Subject)
        result = query.filter(Subject.parent_id == 0).all()
        
        query1 = config.db.session.query(sum(Notebook.value))
        # Check the report parameters
        if self.builder.get_object("allcontent1").get_active() == True:
            query1 = query1.select_from(outerjoin(Subject, Notebook, Subject.id == Notebook.subject_id))
        else:
            query1 = query1.select_from(outerjoin(outerjoin(Notebook, Subject, Notebook.subject_id == Subject.id), 
                                                  Bill, Notebook.bill_id == Bill.id))
            if self.builder.get_object("atdate1").get_active() == True:
                date = self.date.getDateObject()
                query1 = query1.filter(Bill.date == date)
            else:
                if self.builder.get_object("betweendates1").get_active() == True:
                    fdate = self.fdate.getDateObject()
                    tdate = self.tdate.getDateObject()
                    if tdate < fdate:
                        msgbox = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, 
                                                    _("Second date value shouldn't precede the first one."))
                        msgbox.set_title(_("Invalid date order"))
                        msgbox.run()
                        msgbox.destroy()
                        return
                    query1 = query1.filter(Bill.date.between(fdate, tdate))
                
        for s in result:
            res = query1.filter(and_(Subject.lft >= s.lft, Subject.lft <= s.rgt, Notebook.value < 0)).first()
            if res[0] == None:
                debt_sum = 0
            else:
                debt_sum = res[0]
            
            res = query1.filter(and_(Subject.lft >= s.lft, Subject.lft <= s.rgt, Notebook.value > 0)).first()
            if res[0] == None:
                credit_sum = 0
            else:
                credit_sum = res[0]
            
            remain = credit_sum + debt_sum
            if remain < 0:
                remain = "( " + utility.showNumber(-remain) + " )"
            else:
                remain = utility.showNumber(remain)
                
            report_data.append((s.name, utility.showNumber(-debt_sum), utility.showNumber(credit_sum), remain))
            
        return {"data":report_data, "col-width":col_width ,"heading":report_header}
            
    def createPrintJob(self):
        report = self.createReport()
        if report == None:
            return
        if len(report["data"]) == 0:
            msgbox = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, 
                                       _("No ledgers found."))
            msgbox.set_title(_("Empty report"))
            msgbox.run()
            msgbox.destroy()
            return
        
        printjob = printreport.PrintReport(report["data"], report["col-width"], report["heading"])
        todaystr = dateToString(date.today())
        printjob.setHeader(_("Trial Balance"), {_("Date"):todaystr})
        printjob.setDrawFunction("drawTrialReport")
        return printjob
    
    def createPreviewJob(self):
        report = self.createReport()
        if report == None:
            return
        if len(report["data"]) == 0:
            msgbox = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, 
                                       _("No ledgers found."))
            msgbox.set_title(_("Empty report"))
            msgbox.run()
            msgbox.destroy()
            return
            
        preview = previewreport.PreviewReport(report["data"], report["heading"])
        #preview.setHeader(_("Accounting Document"), {_("Document Number"):docnumber, _("Date"):datestr})
        #preview.setDrawFunction("drawDocument")
        return preview
    
    def previewReport(self, sender):
        if platform.system() == 'Windows':
            printjob = self.createPreviewJob()
            if printjob != None:
                printjob.doPreviewJob()
        else:
            printjob = self.createPrintJob()
            if printjob != None:
                printjob.doPrintJob(gtk.PRINT_OPERATION_ACTION_PREVIEW)
    
    def printReport(self, sender):
        printjob = self.createPrintJob()
        if printjob != None:
            printjob.doPrintJob(gtk.PRINT_OPERATION_ACTION_PRINT_DIALOG)
        
    def exportToCSV(self, sender):
        report = self.createReport()
        if report == None:
            return
        
        content = ""
        for key in report["heading"]:
            content += key.replace(",", "") + ","
        content += "\n"
           
        for data in report["data"]:
            for item in data:
                content += item.replace(",", "") + ","
            content += "\n"
            
        dialog = gtk.FileChooserDialog(None, self.window, gtk.FILE_CHOOSER_ACTION_SAVE, (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                                                                         gtk.STOCK_SAVE, gtk.RESPONSE_ACCEPT))
        dialog.run()
        filename = os.path.splitext(dialog.get_filename())[0]
        file = open(filename + ".csv", "w")
        file.write(content)
        file.close()
        dialog.destroy() 
        
    def atdate_toggled(self, sender):
        self.date.set_sensitive(sender.get_active())
        
    def betweendates_toggled(self, sender):
        active = sender.get_active()
        self.fdate.set_sensitive(active)
        self.tdate.set_sensitive(active)
