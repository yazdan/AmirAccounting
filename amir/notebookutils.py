import pygtk
import gtk
from datetime import date

from sqlalchemy import or_, and_
from sqlalchemy.orm.util import outerjoin

from database import *
from amirconfig import config

def arrangeDocuments(parentWin):
    msg = _("This operation may change numbers of permanent documents too.\n\nAre you sure to continue?")
    msgbox = gtk.MessageDialog(parentWin, gtk.DIALOG_MODAL, gtk.MESSAGE_WARNING, gtk.BUTTONS_OK_CANCEL, msg)
    msgbox.set_title(_("Changing document numbers"))
    result = msgbox.run()
    msgbox.destroy()
    if result == gtk.RESPONSE_CANCEL:
        return
    
    query = config.db.session.query(Bill).select_from(Bill)
    query = query.order_by(Bill.date.asc(), Bill.number.asc())
    result = query.all()
    
    num_index = 1
    for b in result:
        b.number = num_index
        num_index += 1
        config.db.session.add(b)
        
    config.db.session.commit()   
    msg = _("Ordering documents completed successfully.")
    msgbox = gtk.MessageDialog(parentWin, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, msg)
    msgbox.set_title(_("Operation successfull"))
    result = msgbox.run()
    msgbox.destroy()      
    
