"""Electrical Work Compacto 0.5.2 - editor autónomo de esquemas eléctricos (sin simulación).

Requisitos: Python 3.9 o superior, Tkinter (incluido normalmente en Windows).
"""
from __future__ import annotations
import json
import base64
import io
import math
import tkinter.font as tkfont
import os
import sys
import tkinter as tk
from tkinter import ttk
from collections import OrderedDict
import quality_render
from page_layout import paper_height,guide_geometry,GREEN,title_block_geometry
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog
from copy import deepcopy
from documentation import (
    GROUPS, documentation_rows, set_description, add_manual_row,
    update_manual_row, delete_documentation_row,
    export_documentation_csv,
)
from pdf_export import export_project_pdf
from core import (
    PAGE_W,PAGE_H,GRID,SYMBOL_NAMES,DEFAULT_REFS,new_document,make_demo,selector_fixed_x,MAX_SELECTOR_POSITIONS,
    make_symbol,make_wire,make_text,make_image,move_element,move_wire,rotate_element,snap,new_id,plc_geometry,MAX_PLC_CHANNELS,
    symbol_shapes,annotation_positions,_rotate,port_positions,wire_connection_target,junction_points,save_document,load_document,export_svg,make_straight_wire,make_rectangle_wire, terminal_label_names, get_terminal_labels, new_project, project_from_document, load_project, save_project, MAX_SHEETS,
)

BG='#e9eff5'
NAVY='#101f32'
NAVY2='#172a42'
TEAL='#00a7a4'
INK='#21364c'
MUTED='#718397'
BORDER='#d8e2ea'
FONT='Segoe UI'

class ElectricalWorkApp:
    def __init__(self, root):
        self.root=root
        self.project=new_project()
        self.sheet_index=0
        self.doc=self.project['sheets'][0]
        self.filepath=None
        self.dirty=False
        self.undo_stack=[]
        self.redo_stack=[]
        self.selected=None
        self.multi_selected=set()
        self.marquee_start=None
        self.marquee_end=None
        self.tool='select'
        self.pending_wire=None
        self.horizontal_first=True
        self.dragging=None
        self._pending_image=None
        self._selector_positions=3
        self._plc_config=(8,8)
        self._plc_brand='' 
        self._plc_model='' 
        self._image_refs=[]
        self._quality_images=[]
        self._symbol_cache=OrderedDict()
        self._documentation_window=None
        # El 100% es el tamaño que permite ver la hoja completa.
        # self.zoom se usa únicamente como escala efectiva de dibujo.
        self.zoom_percent=100.0
        self.zoom=0.65
        self._offset_x=0.0
        self._offset_y=0.0
        self._last_cursor=(0,0)
        self._tool_buttons={}
        self._flyout_buttons={}
        self._contact_popup=None
        self._contact_anchor=None
        self._group_anchors={}
        self._active_flyout=None
        self._title_var=tk.StringVar(value=self.doc['title'])
        self._prop_var=tk.StringVar()
        self._info_var=tk.StringVar()
        self._status_var=tk.StringVar(value='Listo para dibujar')
        self._zoom_var=tk.StringVar(value='100')
        self._selection_var=tk.StringVar(value='Sin selección')
        root.title('Electrical Work · COMPACTO V0.5.2')
        root.configure(bg=BG)
        root.geometry('1450x900')
        root.minsize(980,600)
        try:
            if sys.platform=='win32': root.state('zoomed')
            elif root.tk.call('tk','windowingsystem')=='x11': root.attributes('-zoomed',True)
        except tk.TclError: pass
        root.protocol('WM_DELETE_WINDOW', self.on_close)
        self._build_ui()
        self.root.bind('<Configure>',self._on_window_resize,add='+')
        self._bind_keys()
        self._set_tool('select')
        root.after(60,self.redraw)

    def _btn(self,parent,text,command,bg=NAVY2,fg='#eaf6fc',padx=15,pady=10,**kw):
        return tk.Button(parent,text=text,command=command,font=(FONT,10,'bold'),
                  bg=bg,fg=fg,activebackground=TEAL,activeforeground='white',
                  bd=0,relief='flat',cursor='hand2',padx=padx,pady=pady,
                  highlightthickness=0,**kw)

    def _text(self,par,text,size=10,weight='normal',color=INK,background=None,**kw):
        return tk.Label(par,text=text,font=(FONT,size,weight),fg=color,bg=background or par['bg'],**kw)

    def _make_icon_rail(self,base):
        """Barra CAD compacta: pictogramas técnicos finos, sin nombres visibles."""
        rail=tk.Frame(base,bg='#f7fafc',width=50,
                      highlightthickness=1,highlightbackground=BORDER)
        rail.pack(side='left',fill='y')
        rail.pack_propagate(False)
        self.icon_rail=rail
        self._tool_labels={
            'select':'Puntero: arrastra para mover objetos; en vacío, desplaza la hoja (Esc)',
            'select_box':'Enmarcar: mantén pulsado el botón izquierdo y arrastra para seleccionar componentes y cables',
            'wire_group':'Líneas: recta, codo 90°, rectángulo y selección por recuadro',
            'wire_straight':'Línea libre, también diagonal',
            'wire':'Cable con codo a 90°',
            'wire_rectangle':'Cuadrado / rectángulo',
            'contact_group':'Contactos e interruptores: NA, NC y doble contacto',
            'coil_group':'Bobinas: bobina, temporizadores y electroválvula',
            'pushbutton_group':'Mando: pulsadores abiertos/cerrados, emergencia y selectores',
            'protection_group':'Protección: fusible, seccionador, automáticos, diferenciales, guardamotor y térmico',
            'power_group':'Potencia: contactor tripolar y motores',
            'signal_group':'Señalización y medida',
            'sensor_group':'Sensores: inductivo, capacitivo, magnético y barrera fotoeléctrica',
            'process_group':'Presostato, vacuostato y termostato',
            'terminal_group':'Conexiones: borne, salida/entrada de página, unión y tierra',
            'plc_group':'Señales de PLC: entrada y salida digitales',
            'plc_module':'PLC configurable (entradas, salidas y bornes + / −)',
            'text':'Añadir texto',
        }
        self._tool_labels.update(SYMBOL_NAMES)
        self._groups={
            'wire_group':('wire_straight','select_box','wire','wire_rectangle'),
            'contact_group':('contact_no','contact_nc',
                             'switch_horizontal_no','switch_horizontal_nc',
                             'switch_double_horizontal',
                             'contact_timer_no','contact_timer_nc','thermal_nc','thermal_no',
                             'limit_no','limit_nc'),
            'coil_group':('coil','coil_timer_on','coil_timer_off','coil_solenoid'),
            'pushbutton_group':('pushbutton','pushbutton_nc',
                                'pushbutton_horizontal_no','pushbutton_horizontal_nc',
                                'pushbutton_double','emergency_nc','selector_no','selector_nc','selector_multi'),
            'protection_group':('fuse','disconnect_1p','breaker_1p','breaker_2p','breaker_3p','breaker_4p','differential_2p','differential_4p','motor_protector_3p','thermal_3p'),
            'power_group':('contactor_3p','motor_1ph','motor_3ph'),
            'signal_group':('lamp','buzzer','voltmeter','ammeter'),
            'sensor_group':('sensor_inductive_no','sensor_inductive_nc','sensor_capacitive_no','sensor_capacitive_nc','sensor_magnetic_no','sensor_magnetic_nc','photoelectric_barrier'),
            'process_group':('pressostat','vacuostat','thermostat'),
            'terminal_group':('terminal','directional_terminal','directional_terminal_in','junction','ground'),
            'plc_group':('plc_input','plc_output'),
        }
        self._group_icon={group:options[0] for group,options in self._groups.items()}
        self._tooltip=None
        for index,tool in enumerate(('select','wire_group','contact_group',
                     'coil_group','pushbutton_group','protection_group',
                     'power_group','signal_group','sensor_group','process_group','terminal_group',
                     'plc_group','plc_module','power_supply','text')):
            if index in (2,5,7,10):
                tk.Frame(rail,height=1,bg='#d9e2e9').pack(fill='x',padx=8,pady=4)
            cv=tk.Canvas(rail,width=34,height=32,highlightthickness=1,
                         highlightbackground='#f7fafc',bg='#f7fafc',bd=0,
                         relief='flat',cursor='hand2',takefocus=1)
            cv.pack(padx=6,pady=2)
            if tool in self._groups:
                choose=lambda event,t=tool:self._toggle_tool_group(t,event)
                self._group_anchors[tool]=cv
            elif tool=='plc_module':
                choose=lambda event:self._select_plc_tool()
            else:
                choose=lambda event,t=tool:self._set_tool(t)
            cv.bind('<Button-1>',choose)
            cv.bind('<Return>',choose)
            cv.bind('<space>',choose)
            cv.bind('<Enter>',lambda e,t=tool:self._show_tooltip(e,t))
            cv.bind('<Leave>',lambda e:self._hide_tooltip())
            self._tool_buttons[tool]=cv
        self._contact_anchor=self._group_anchors['contact_group']
        self._paint_icons()

    def _plc_counts_dialog(self,initial=None):
        """Solicita cantidades y textos del PLC; None indica cancelación."""
        initial=initial or (self._plc_config[0], self._plc_config[1], self._plc_brand, self._plc_model)
        dialog=tk.Toplevel(self.root)
        dialog.title('Configurar PLC')
        dialog.transient(self.root);dialog.resizable(False,False)
        dialog.configure(bg='#f8fbfd')
        panel=tk.Frame(dialog,padx=18,pady=16,bg='#f8fbfd');panel.pack(fill='both')
        tk.Label(panel,text='Nuevo PLC',font=(FONT,12,'bold'),bg='#f8fbfd',fg=INK).pack(anchor='w',pady=(0,10))
        fields=[('Número de entradas digitales', str(initial[0])),('Número de salidas digitales', str(initial[1])),('Marca', initial[2]),('Modelo', initial[3])]
        vars=[]
        for idx,(caption,val) in enumerate(fields):
            tk.Label(panel,text=caption,bg='#f8fbfd',fg=INK).pack(anchor='w')
            sv=tk.StringVar(value=val)
            ent=tk.Entry(panel,textvariable=sv,width=28,justify='center' if idx<2 else 'left',font=(FONT,11))
            ent.pack(fill='x',pady=(3,11 if idx<3 else 8))
            vars.append((sv,ent))
        tk.Label(panel,text=f'Entre 0 y {MAX_PLC_CHANNELS} cada uno; al menos una señal.\nSe añadirán bornes 24v y 0v.', bg='#f8fbfd',fg=MUTED,justify='left').pack(anchor='w',pady=(0,12))
        result=[None]
        def accept():
            try:
                a,b=int(vars[0][0].get()),int(vars[1][0].get())
                from core import _check_plc_counts
                _check_plc_counts(a,b)
            except (ValueError,TypeError):
                messagebox.showwarning('PLC','Introduce cantidades válidas de entradas y salidas.',parent=dialog)
                return
            brand=vars[2][0].get().strip()
            model=vars[3][0].get().strip()
            result[0]=(a,b,brand[:120],model[:120]);dialog.destroy()
        buttons=tk.Frame(panel,bg='#f8fbfd');buttons.pack(anchor='e')
        tk.Button(buttons,text='Cancelar',command=dialog.destroy).pack(side='left',padx=5)
        tk.Button(buttons,text='Aceptar',command=accept,bg=TEAL,fg='white').pack(side='left')
        dialog.bind('<Return>',lambda e:accept())
        dialog.bind('<Escape>',lambda e:dialog.destroy())
        dialog.protocol('WM_DELETE_WINDOW',dialog.destroy)
        dialog.grab_set();vars[0][1].focus_set();self.root.wait_window(dialog)
        return result[0]

    def _select_plc_tool(self):
        chosen=self._plc_counts_dialog()
        if chosen is not None:
            self._plc_config=(chosen[0],chosen[1])
            self._plc_brand=chosen[2]
            self._plc_model=chosen[3]
            self._set_tool('plc_module')

    def _toggle_contact_group(self, event=None):
        """Nombre anterior conservado para compatibilidad con pruebas V0.5."""
        return self._toggle_tool_group('contact_group',event)

    def _toggle_tool_group(self,group,event=None):
        """Desplegable común hacia la derecha para contactos, pulsadores y líneas."""
        if self._contact_popup is not None:
            was_same=self._active_flyout==group
            self._close_contact_popup()
            if was_same:return 'break'
        # En el grupo de líneas la opción predeterminada debe ser la recta.
        if group=='wire_group':
            self.tool='wire_straight'
            self.pending_wire=None
            self.dragging=None
            self._info_var.set('Línea recta de cualquier inclinación: haz clic en inicio y final.')
            self._status_var.set('Herramienta: Recta')
            self.canvas.configure(cursor='crosshair')
        self._paint_icons()
        self._hide_tooltip()
        menu=tk.Frame(self._icon_base,bg='#ffffff',relief='solid',bd=1,
                      highlightthickness=1,highlightbackground='#a3beca')
        self._contact_popup=menu
        self._active_flyout=group
        self._flyout_buttons={}
        for tool in self._groups[group]:
            cv=tk.Canvas(menu,width=34,height=32,highlightthickness=1,
                         highlightbackground='#ffffff',bg='#ffffff',bd=0,
                         cursor='hand2',takefocus=1)
            cv.pack(side='left',padx=5,pady=5)
            cv.bind('<Button-1>',lambda e,t=tool:self._choose_symbol_tool(t))
            cv.bind('<Return>',lambda e,t=tool:self._choose_symbol_tool(t))
            cv.bind('<space>',lambda e,t=tool:self._choose_symbol_tool(t))
            cv.bind('<Enter>',lambda e,t=tool:self._show_tooltip(e,t))
            cv.bind('<Leave>',lambda e:self._hide_tooltip())
            self._flyout_buttons[tool]=cv
        self._icon_base.update_idletasks()
        anchor=self._group_anchors[group]
        menu.place(x=self.icon_rail.winfo_width()+3,y=anchor.winfo_y())
        menu.lift()
        self._paint_icons()
        self._flyout_buttons[self._groups[group][0]].focus_set()
        return 'break'

    def _selector_positions_dialog(self,initial=None):
        """Pregunta las posiciones como el configurador del PLC."""
        dialog=tk.Toplevel(self.root)
        dialog.title('Configurar selector')
        dialog.transient(self.root)
        dialog.resizable(False,False)
        dialog.configure(bg='#f8fbfd')
        body=tk.Frame(dialog,bg='#f8fbfd',padx=20,pady=17)
        body.pack(fill='both')
        tk.Label(body,text='Selector multiposición',bg='#f8fbfd',fg=INK,
                 font=(FONT,12,'bold')).pack(anchor='w',pady=(0,12))
        tk.Label(body,text='Número de posiciones',bg='#f8fbfd',fg=INK).pack(anchor='w')
        count=tk.StringVar(value=str(initial if initial is not None else self._selector_positions))
        field=tk.Spinbox(body,from_=2,to=MAX_SELECTOR_POSITIONS,
                         textvariable=count,width=9,justify='center',font=(FONT,12))
        field.pack(anchor='w',pady=(4,12))
        tk.Label(body,text='Se dibujará un borne común y una salida por posición.\n'
                           'Podrás editar y numerar los bornes después.',
                 justify='left',bg='#f8fbfd',fg=MUTED,font=(FONT,9)).pack(anchor='w',pady=(0,12))
        bar=tk.Frame(body,bg='#f8fbfd');bar.pack(anchor='e')
        result=[None]
        def accept(event=None):
            try:
                value=int(count.get())
                if not 2 <= value <= MAX_SELECTOR_POSITIONS:raise ValueError()
            except ValueError:
                messagebox.showwarning('Selector','Introduce un número entero entre 2 y 12.',parent=dialog)
                return
            result[0]=value
            dialog.destroy()
        tk.Button(bar,text='Cancelar',command=dialog.destroy,bg='#e9eff5',relief='flat',padx=12,pady=6).pack(side='left',padx=4)
        tk.Button(bar,text='Aceptar',command=accept,bg=TEAL,fg='white',relief='flat',padx=12,pady=6).pack(side='left')
        dialog.bind('<Return>',accept)
        dialog.bind('<Escape>',lambda e:dialog.destroy())
        dialog.protocol('WM_DELETE_WINDOW',dialog.destroy)
        dialog.update_idletasks()
        x=self.root.winfo_rootx()+(self.root.winfo_width()-dialog.winfo_width())//2
        y=self.root.winfo_rooty()+(self.root.winfo_height()-dialog.winfo_height())//2
        dialog.geometry(f'+{max(0,x)}+{max(0,y)}')
        field.focus_set();field.selection_range(0,'end')
        dialog.grab_set();self.root.wait_window(dialog)
        return result[0]

    def _choose_symbol_tool(self,tool):
        if tool=='selector_multi':
            chosen=self._selector_positions_dialog()
            if chosen is None:return 'break'
            self._selector_positions=chosen
        self._set_tool(tool)
        return 'break'

    def _close_contact_popup(self):
        if self._contact_popup is not None:
            self._contact_popup.destroy()
            self._contact_popup=None
        self._active_flyout=None
        self._flyout_buttons={}
        self._hide_tooltip()

    def _close_contact_popup_outside(self,event):
        """Cierra solo cuando se pulsa fuera del desplegable activo."""
        if self._contact_popup is None:return
        widget=event.widget
        if widget is self._group_anchors.get(self._active_flyout):return
        while widget is not None:
            if widget is self._contact_popup:return
            widget=getattr(widget,'master',None)
        self._close_contact_popup()

    def _show_tooltip(self,event=None,tool=None):
        # Ayuda instantánea EXCLUSIVA de herramientas laterales.
        if event is None or tool is None:return
        self._hide_tooltip()
        label=self._tool_labels.get(tool,tool)
        popup=tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.configure(bg='#ecf5f7')
        tk.Label(popup,text=label,bg='#ecf5f7',fg=INK,
                 font=(FONT,9),padx=8,pady=4).pack()
        popup.update_idletasks()
        x=event.widget.winfo_rootx()+event.widget.winfo_width()+7
        y=event.widget.winfo_rooty()+3
        popup.geometry(f'+{x}+{y}')
        self._tooltip=popup

    def _hide_tooltip(self):
        if self._tooltip is not None:
            self._tooltip.destroy()
            self._tooltip=None

    def _bind_tip(self,widget,text):
        # Sin ayudas en botones superiores, campo de zoom ni menús.
        return None

    def _paint_icons(self):
        """Dibuja iconos de 24 px a escala constante, sin deformar símbolos."""
        for tool,cv in list(self._tool_buttons.items())+list(self._flyout_buttons.items()):
            selected=(tool==self.tool or (tool in self._groups and self.tool in self._groups[tool]))
            bg='#e5f7f4' if selected else '#f7fafc'
            fg='#067b78' if selected else '#30495b'
            cv.configure(bg=bg,highlightbackground='#9dd3ca' if selected else bg)
            cv.delete('all')
            def line(*points,width=1.45,dash=None):
                opts={'fill':fg,'width':width,'capstyle':'round','joinstyle':'round'}
                if dash:opts['dash']=dash
                cv.create_line(*points,**opts)
            def rect(x1,y1,x2,y2,width=1.45):
                cv.create_rectangle(x1,y1,x2,y2,fill=bg,outline=fg,width=width)
            def ring(x,y,r=2.0):
                cv.create_oval(x-r,y-r,x+r,y+r,fill=bg,outline=fg,width=1.25)
            if tool=='select':
                cv.create_polygon(10,6,12,26,17,21,20,28,23,27,20,19,26,18,
                                  fill=fg,outline=fg)
            elif tool in ('wire','wire_group'):
                line(8,26,8,9,28,9)
                ring(8,26,1.6);ring(28,9,1.6)
                if tool=='wire_group':
                    cv.create_polygon(29,24,33,26.5,29,29,fill=fg,outline=fg)
            elif tool=='select_box':
                rect(8,9,27,26,width=1.3)
                cv.create_rectangle(11,12,17,18,outline=fg,fill=bg,width=1)
                cv.create_line(7,7,11,7,fill=fg,dash=(2,2))
            elif tool=='wire_straight':
                line(7,26,28,7)
                ring(7,26,1.8);ring(28,7,1.8)
            elif tool=='wire_rectangle':
                rect(9,8,27,26)
                ring(9,8,1.5);ring(27,26,1.5)
            elif tool=='plc_module':
                cv.create_rectangle(8,5,28,28,outline=fg,width=1.25)
                cv.create_text(18,16,text='PLC',fill=fg,font=(FONT,7,'bold'))
                for yy in (11,18,25):
                    line(5,yy,8,yy);line(28,yy,31,yy)
            elif tool in SYMBOL_NAMES or tool in self._groups:
                # Un único motor de formas para plano, SVG y todas las miniaturas.
                # Evita que los iconos con dibujos antiguos no coincidan con
                # la simbología realmente colocada en el esquema.
                self._paint_symbol_preview(cv,self._group_icon.get(tool,tool),fg,bg)
                if tool in self._groups:
                    cv.create_polygon(29,24,33,26.5,29,29,fill=fg,outline=fg)
            elif tool=='text':
                cv.create_text(18,16,text='A',font=(FONT,18,'bold'),fill=fg)
            else:
                self._paint_symbol_preview(cv,self._group_icon.get(tool,tool),fg,bg)
                if tool in self._groups:
                    cv.create_polygon(29,24,33,26.5,29,29,fill=fg,outline=fg)

    def _paint_symbol_preview(self,canvas,kind,fg,bg):
        # Miniatura CAD generada desde la misma geometría del plano.
        from symbology import compact_symbol_primitives
        factor=.16 if kind in ('selector_multi','switch_double_horizontal',
                               'switch_horizontal_no','switch_horizontal_nc',
                               'pushbutton_horizontal_no','pushbutton_horizontal_nc') else (
                 .18 if kind=='breaker_4p' else (.23 if kind=='pushbutton_double' else (.25 if kind=='coil_solenoid' else .30)))
        def xy(x,y):return 18+x*factor,16+y*factor
        for primitive in compact_symbol_primitives(kind):
            typ=primitive[0]
            if typ in ('line','dashline'):
                canvas.create_line(*xy(primitive[1],primitive[2]),
                    *xy(primitive[3],primitive[4]),fill=fg,width=1.2,
                    dash=(3,2) if typ=='dashline' else ())
            elif typ in ('rect','fillrect'):
                a,b,c,d=primitive[1:]
                canvas.create_rectangle(*xy(a,b),*xy(c,d),fill=fg if typ=='fillrect' else bg,outline=fg,width=1.1)
            elif typ in ('circle','dot'):
                x,y=xy(primitive[1],primitive[2]);r=primitive[3]*factor
                canvas.create_oval(x-r,y-r,x+r,y+r,
                    fill=fg if typ=='dot' else bg,outline=fg,width=1.1)
            elif typ in ('glyph','mark'):
                x,y=xy(primitive[1],primitive[2])
                canvas.create_text(x,y,text=primitive[3],fill=fg,
                    font=(FONT,max(5,int(primitive[4]*factor)),'bold'),
                    anchor='center' if typ=='mark' else 'w')

    def _build_ui(self):
        # Cabecera reducida: recuperar altura útil sin cambiar su estilo.
        top=tk.Frame(self.root,bg=NAVY,height=54)
        top.pack(fill='x',side='top')
        top.pack_propagate(False)
        brand=tk.Frame(top,bg=NAVY)
        brand.pack(side='left',fill='y',padx=(12,0))
        tk.Label(brand,text='EW',font=(FONT,12,'bold'),fg='white',bg=TEAL,
                 width=3,height=2).pack(side='left',pady=8)
        titlebox=tk.Frame(brand,bg=NAVY)
        titlebox.pack(side='left',padx=10,pady=7)
        self._text(titlebox,'ELECTRICAL WORK',12,'bold','#ffffff').pack(anchor='w')
        self._text(titlebox,'EDITOR DE ESQUEMAS · COMPACTO 70 % · V0.5',8,'normal','#9db2c5').pack(anchor='w')
        actions=tk.Frame(top,bg=NAVY)
        actions.pack(side='right',padx=(0,12),pady=9)
        for name,command,bg in [
            ('Nuevo',self.new_file,NAVY2),('Abrir',self.open_file,NAVY2),
            ('Guardar',self.save_file,TEAL),('Documentación',self.open_documentation,NAVY2),
            ('Exportar PDF',self.export_pdf_dialog,NAVY2),
            ('Salir',self.on_close,NAVY2)]:
            btn=self._btn(actions,name,command,bg=bg,padx=10,pady=6)
            btn.config(font=(FONT,9,'bold'))
            btn.pack(side='left',padx=3)

        base=tk.Frame(self.root,bg=BG)
        self._icon_base=base
        base.pack(fill='both',expand=True)
        # Conserva únicamente la columna de herramientas a la izquierda.
        self._make_icon_rail(base)
        middle=tk.Frame(base,bg=BG)
        middle.pack(side='left',fill='both',expand=True)

        # Barra de edición compacta: reemplaza por completo las propiedades
        # de la derecha y las indicaciones de rejilla/tamaño sin utilidad.
        strip=tk.Frame(middle,bg='#f8fbfd',height=46)
        strip.pack(fill='x')
        strip.pack_propagate(False)
        self.edit_toolbar=strip
        left=tk.Frame(strip,bg='#f8fbfd')
        left.pack(side='left',fill='y',padx=(10,0))
        def action(name,callback,description,attr=None,bg='#edf3f7',fg=INK):
            btn=self._btn(left,name,callback,bg=bg,fg=fg,padx=9,pady=5)
            btn.configure(font=(FONT,9,'bold'))
            btn.pack(side='left',padx=2,pady=7)
            self._bind_tip(btn,description)
            if attr:setattr(self,attr,btn)
            return btn
        action('↶  Deshacer',self.undo,'Deshacer el último cambio  ·  Ctrl+Z')
        action('↷  Rehacer',self.redo,'Rehacer el cambio  ·  Ctrl+Y')
        tk.Frame(left,width=1,bg=BORDER).pack(side='left',fill='y',padx=8,pady=11)
        # Un solo botón Girar (cuatro pulsaciones completan 360°).
        action('⟳  Girar',lambda:self.rotate_selected(1),
               'Girar 90° hacia la derecha','rotate_right_button')
        self.rotate_left_button=self.rotate_right_button
        self.rotate_button=self.rotate_right_button
        # Alias interno sin botón visible: la edición se hace con doble clic.
        self.edit_button=tk.Button(left,command=self.edit_selected_dialog)
        action('Imagen',self.insert_image_dialog,'Insertar imagen en el plano','image_button')
        action('Duplicar',self.duplicate_selected,
               'Duplicar el elemento o cable seleccionado','duplicate_button')
        action('Borrar',self.delete_selected,
               'Eliminar selección  ·  Supr','delete_button',bg='#faecee',fg='#8e3f48')
        action('Título',self.edit_title_dialog,'Cambiar el título del plano')
        self._main_toolbar_buttons=[w for w in left.winfo_children() if isinstance(w,tk.Button)]
        # Control multipágina junto a Título, en LA MISMA barra de edición.
        self.sheets_bar=tk.Frame(left,bg='#f8fbfd')
        sheets_bar=self.sheets_bar
        sheets_bar.pack(side='left',fill='y',padx=(4,0))
        def sheet_button(label,func,bg='#edf3f7'):
            b=self._btn(sheets_bar,label,func,bg=bg,fg=INK,padx=4,pady=5)
            b.configure(font=(FONT,8,'bold'))
            b.pack(side='left',padx=1,pady=7)
            return b
        self.sheet_prev_button=sheet_button('◀',lambda:self.switch_sheet(self.sheet_index-1))
        self._sheet_var=tk.StringVar()
        self.sheet_picker=ttk.Combobox(sheets_bar,textvariable=self._sheet_var,width=58,
                                      state='readonly',font=(FONT,8))
        self.sheet_picker.pack(side='left',padx=2,pady=7)
        self.sheet_picker.bind('<<ComboboxSelected>>',self._choose_sheet)
        self.sheet_next_button=sheet_button('▶',lambda:self.switch_sheet(self.sheet_index+1))
        self.sheet_move_up_button=sheet_button('↑ Hoja',lambda:self.move_sheet(-1))
        self.sheet_move_down_button=sheet_button('↓ Hoja',lambda:self.move_sheet(1))
        self.sheet_add_button=sheet_button('+ Hoja',self.add_sheet)
        self.sheet_delete_button=sheet_button('Eliminar',self.delete_sheet,bg='#faecee')
        self.sheet_rename_button=sheet_button('Nombre',self.rename_sheet)
        self.sheet_project_button=sheet_button('Proyecto',self.rename_project)
        self.sheet_menu_button=tk.Menubutton(sheets_bar,text='Hojas ▾',bg='#edf3f7',
                     fg=INK,font=(FONT,8,'bold'),relief='flat',padx=5,pady=5,
                     activebackground='#d9eaf0',cursor='hand2')
        self.sheet_menu=tk.Menu(self.sheet_menu_button,tearoff=False)
        for text,callback in (('+ Añadir hoja',self.add_sheet),
                              ('Eliminar hoja',self.delete_sheet),
                              ('Renombrar hoja',self.rename_sheet),
                              ('Proyecto',self.rename_project),
                              ('↑ Subir hoja',lambda:self.move_sheet(-1)),
                              ('↓ Bajar hoja',lambda:self.move_sheet(1))):
            self.sheet_menu.add_command(label=text,command=callback)
        self.sheet_menu_button.configure(menu=self.sheet_menu)
        self._compact_toolbar=None
        self._refresh_sheets()


        zoom_controls=tk.Frame(strip,bg='#f8fbfd')
        zoom_controls.pack(side='right',fill='y',padx=(2,12))
        zoom_out=self._btn(zoom_controls,'−',lambda:self.set_zoom(self.zoom_percent-10),
                            bg='#edf3f7',fg=INK,padx=9,pady=5)
        zoom_out.configure(font=(FONT,11,'bold'))
        zoom_out.pack(side='left',pady=7)
        self._bind_tip(zoom_out,'Reducir zoom en 10 puntos porcentuales')
        self.zoom_entry=tk.Entry(zoom_controls,textvariable=self._zoom_var,width=5,
            justify='center',font=(FONT,10,'bold'),fg=INK,bg='white',
            relief='solid',bd=1,highlightthickness=1,highlightbackground=BORDER)
        self.zoom_entry.pack(side='left',padx=(7,2),ipady=5)
        self.zoom_entry.bind('<Return>',self.apply_zoom_entry)
        self.zoom_entry.bind('<KP_Enter>',self.apply_zoom_entry)
        self.zoom_entry.bind('<FocusOut>',self.apply_zoom_entry)
        self._text(zoom_controls,'%',9,'bold',INK).pack(side='left',padx=(0,7))
        zoom_in=self._btn(zoom_controls,'+',lambda:self.set_zoom(self.zoom_percent+10),
                           bg='#edf3f7',fg=INK,padx=9,pady=5)
        zoom_in.configure(font=(FONT,11,'bold'))
        zoom_in.pack(side='left',pady=7)
        self._bind_tip(zoom_in,'Aumentar zoom en 10 puntos porcentuales')
        self._bind_tip(self.zoom_entry,'Indica el porcentaje exacto y pulsa Intro. 100 % = hoja entera')
        zoom_controls.pack_forget()
        zoom_controls.pack(side='right',fill='y',padx=(2,7),before=left)

        workspace=tk.Frame(middle,bg=BG)
        workspace.pack(fill='both',expand=True)
        self.canvas=tk.Canvas(workspace,bg=BG,highlightthickness=0,bd=0,confine=True)
        self.canvas.grid(row=0,column=0,sticky='nsew')
        xbar=tk.Scrollbar(workspace,orient='horizontal',command=self.canvas.xview)
        ybar=tk.Scrollbar(workspace,orient='vertical',command=self.canvas.yview)
        xbar.grid(row=1,column=0,sticky='ew')
        ybar.grid(row=0,column=1,sticky='ns')
        self.canvas.configure(xscrollcommand=xbar.set,yscrollcommand=ybar.set)
        self._xbar=xbar
        self._ybar=ybar
        self._scrollbars_visible=True
        workspace.grid_rowconfigure(0,weight=1)
        workspace.grid_columnconfigure(0,weight=1)
        self.canvas.bind('<Button-1>',self.on_canvas_down)
        self.canvas.bind('<Double-Button-1>',self.on_canvas_double)
        self.canvas.bind('<B1-Motion>',self.on_canvas_drag)
        self.canvas.bind('<ButtonRelease-1>',self.on_canvas_up)
        self.canvas.bind('<Motion>',self.on_motion)
        self.canvas.bind('<MouseWheel>',self.on_mousewheel)
        self.canvas.bind('<Button-4>',self.on_mousewheel)
        self.canvas.bind('<Button-5>',self.on_mousewheel)
        self.canvas.bind('<Button-3>',self.on_canvas_context)
        self.canvas.bind('<Configure>',lambda e:self.redraw())
        self._update_properties()

    def _on_window_resize(self,event):
        if event.widget is self.root:
            self._responsive_toolbar(event.width)

    def _responsive_toolbar(self,window_width):
        """Cuando no cabe la barra completa, agrupar acciones en un menú.

        La navegación permanece pegada a Título y el zoom accesible.
        El modo completo se mantiene al trabajar con ventana maximizada.
        """
        # El nombre de hoja tiene prioridad sobre botones secundarios.
        # A anchuras intermedias, esos botones se agrupan en «Hojas».
        full=window_width >= 1890
        picker_width=(58 if full else 64 if window_width >= 1460
                      else 55 if window_width >= 1300
                      else 50 if window_width >= 1190
                      else 41 if window_width >= 1100
                      else 33 if window_width >= 1020 else 25)
        state=(full,picker_width)
        if self._compact_toolbar == state:return
        self._compact_toolbar=state
        for button in self._main_toolbar_buttons:
            button.configure(padx=9 if full else 4)
        controls=(self.sheet_add_button,self.sheet_delete_button,
                  self.sheet_rename_button,self.sheet_project_button,
                  self.sheet_move_up_button,self.sheet_move_down_button)
        if full:
            self.sheet_menu_button.pack_forget()
            for btn in controls:btn.pack(side='left',padx=1,pady=7)
        else:
            for btn in controls:btn.pack_forget()
            self.sheet_menu_button.pack(side='left',padx=2,pady=7)
        self.sheet_picker.configure(width=picker_width)

    def _bind_keys(self):
        self.root.bind('<Control-n>',lambda e:self.new_file())
        self.root.bind('<Control-o>',lambda e:self.open_file())
        self.root.bind('<Control-s>',lambda e:self.save_file())
        self.root.bind('<Control-Shift-S>',lambda e:self.save_as())
        self.root.bind('<Control-z>',lambda e:self.undo())
        self.root.bind('<Control-y>',lambda e:self.redo())
        self.root.bind('<Escape>',self.return_to_pointer)
        self.root.bind('<Delete>',self._key_delete)
        self.root.bind('<BackSpace>',self._key_delete)
        self.root.bind('<KeyPress-r>',self._key_rotate)
        self.root.bind('<space>',self._key_space)
        self.root.bind_all('<Button-1>',self._close_contact_popup_outside,add='+')

    def _entry_focused(self):
        return isinstance(self.root.focus_get(),(tk.Entry,tk.Text))

    def _key_delete(self,event):
        if not self._entry_focused(): self.delete_selected()

    def _key_rotate(self,event):
        if not self._entry_focused(): self.rotate_selected()

    def _key_space(self,event):
        if self._entry_focused(): return
        if self.tool=='wire':
            self.horizontal_first=not self.horizontal_first
            self._status_var.set('Codo del cable: '+('horizontal primero' if self.horizontal_first else 'vertical primero'))
            self.redraw()

    def _set_tool(self,tool):
        self._close_contact_popup()
        if tool!='image':self._pending_image=None
        self.tool=tool
        self.pending_wire=None
        self.dragging=None
        self.marquee_start=self.marquee_end=None
        descriptions={
            'select':'Rueda para ampliar o reducir. Arrastra desde el vacío para desplazar la hoja; sobre un elemento lo mueves. Para seleccionar varios, usa el recuadro del desplegable Líneas.',
            'select_box':'MODO ENMARCAR: pulsa y arrastra sobre el dibujo para marcar componentes o cables. No desplaza la hoja. Al soltar puedes mover el grupo con el puntero.',
            'wire':'Cable a 90°: inicio y final. Indicador verde en uniones. Espacio cambia la posición del codo.',
            'wire_straight':'Línea recta de cualquier inclinación: haz clic en inicio y final.',
            'wire_rectangle':'Cuadrado / rectángulo: haz clic en dos esquinas opuestas.',
            'text':'Haz clic sobre la hoja y escribe el texto que quieras colocar.',
        }
        self._info_var.set(descriptions.get(tool,'Haz clic sobre la hoja para colocar un '+SYMBOL_NAMES.get(tool,'elemento')+'.'))
        self._paint_icons()
        self._hide_tooltip()
        self._status_var.set('Herramienta: '+({'select':'Puntero','select_box':'Enmarcar selección','wire':'Cable 90°','wire_straight':'Recta','wire_rectangle':'Rectángulo','text':'Texto'}.get(tool,SYMBOL_NAMES.get(tool,tool))))
        self.canvas.configure(cursor='arrow' if tool=='select' else 'crosshair')
        self.redraw()

    def _point(self,e):
        return (self.canvas.canvasx(e.x)-self._offset_x)/self.zoom,(self.canvas.canvasy(e.y)-self._offset_y)/self.zoom

    def _xy(self,x,y):
        return x*self.zoom+self._offset_x,y*self.zoom+self._offset_y

    def _page_point(self,e):
        x,y=self._point(e)
        x,y=snap(x),snap(y)
        x=max(GRID,min(PAGE_W-GRID,x))
        y=max(GRID,min(PAGE_H-GRID,y))
        return x,y

    def _wire_target(self,x,y):
        # La tolerancia es visible y estable en pantalla incluso con zoom.
        return wire_connection_target(self.doc,x,y,tolerance=12/self.zoom)

    def _wire_xy(self,x,y):
        target=self._wire_target(x,y)
        return target['point'] if target else (snap(x),snap(y))

    def _hit(self,e):
        cx=self.canvas.canvasx(e.x)
        cy=self.canvas.canvasy(e.y)
        matches=self.canvas.find_overlapping(cx-7,cy-7,cx+7,cy+7)
        for oid in reversed(matches):
            tags=self.canvas.gettags(oid)
            for tag in tags:
                if tag.startswith('element:'):return ('element',tag[8:])
                if tag.startswith('wire:'):return ('wire',tag[5:])
        return None

    def _hit_annotation(self,e):
        """Detecta exclusivamente el texto, no la zona general del símbolo."""
        cx=self.canvas.canvasx(e.x)
        cy=self.canvas.canvasy(e.y)
        for oid in reversed(self.canvas.find_overlapping(cx-1,cy-2,cx+1,cy+2)):
            for tag in self.canvas.gettags(oid):
                if tag.startswith('annotation:'):
                    _,ident,key=tag.split(':',2)
                    if any(el['id']==ident for el in self.doc['elements']):
                        return ident,key
        return None

    def on_canvas_context(self,event):
        """Restablecer la posición de una numeración sin editar el dibujo."""
        if self.tool!='select':
            self.cancel_pending()
            return 'break'
        found=self._hit_annotation(event)
        if not found:return 'break'
        ident,key=found
        el=next((item for item in self.doc['elements'] if item['id']==ident),None)
        if el is None:return 'break'
        menu=tk.Menu(self.root,tearoff=False)
        offsets=el.get('annotation_offsets',{})
        def restore_one():
            if key not in el.get('annotation_offsets',{}):return
            self._history()
            el['annotation_offsets'].pop(key,None)
            if not el['annotation_offsets']:el.pop('annotation_offsets',None)
            self._changed()
        def restore_all():
            if not el.get('annotation_offsets'):return
            self._history()
            el.pop('annotation_offsets',None)
            self._changed()
        menu.add_command(label='Restablecer esta etiqueta',command=restore_one,
                         state='normal' if key in offsets else 'disabled')
        menu.add_command(label='Restablecer todas las etiquetas del elemento',command=restore_all,
                         state='normal' if offsets else 'disabled')
        try:menu.tk_popup(event.x_root,event.y_root)
        finally:menu.grab_release()
        return 'break'

    def _in_page(self,p):
        x,y=p
        return 0<=x<=PAGE_W and 0<=y<=PAGE_H

    def _selection_items(self):
        items=set(self.multi_selected)
        if self.selected:items.add(self.selected)
        return items

    def _group_bounds(self,items):
        xs=[];ys=[]
        for typ,ident in items:
            if typ=='element':
                el=next((e for e in self.doc['elements'] if e['id']==ident),None)
                if el is not None:
                    xs.append(el['x']); ys.append(el['y'])
            elif typ=='wire':
                wire=next((w for w in self.doc['wires'] if w['id']==ident),None)
                if wire is not None:
                    xs.extend(x for x,_ in wire['points']); ys.extend(y for _,y in wire['points'])
        if not xs:return None
        return min(xs),min(ys),max(xs),max(ys)

    @staticmethod
    def _segment_intersects_area(a,b,left,top,right,bottom):
        """Liang-Barsky: detecta también cables que cruzan el recuadro."""
        x1,y1=a;x2,y2=b
        dx=x2-x1;dy=y2-y1
        enter,leave=0.,1.
        for p,q in ((-dx,x1-left),(dx,right-x1),(-dy,y1-top),(dy,bottom-y1)):
            if p==0:
                if q<0:return False
            else:
                t=q/p
                if p<0:enter=max(enter,t)
                else:leave=min(leave,t)
                if enter>leave:return False
        return True

    def _objects_in_area(self,left,top,right,bottom):
        """Encuentra dibujos visibles tocados por un marco de selección.

        Para símbolos e imágenes usa la caja real renderizada, incluyendo
        numeraciones; para cables examina cada segmento, no solo sus extremos.
        """
        ax,ay=self._xy(left,top)
        bx,by=self._xy(right,bottom)
        found=set()
        for item in self.doc['elements']:
            box=self.canvas.bbox(f'element:{item["id"]}')
            if box and box[0]<=bx and box[2]>=ax and box[1]<=by and box[3]>=ay:
                found.add(('element',item['id']))
        for wire in self.doc['wires']:
            if any(self._segment_intersects_area(a,b,left,top,right,bottom)
                   for a,b in zip(wire['points'],wire['points'][1:])):
                found.add(('wire',wire['id']))
        return found

    def on_canvas_down(self,e):
        # El modo de encuadre es deliberado y no interfiere con arrastrar la hoja.
        if self.tool=='select_box':
            self.dragging=None
            self.marquee_start=self._point(e)
            self.marquee_end=self.marquee_start
            self.redraw()
            return 'break'
        x,y=self._page_point(e)
        if self.tool=='select':
            annotation=self._hit_annotation(e)
            if annotation is not None:
                ident,key=annotation
                item=next((i for i in self.doc['elements'] if i['id']==ident),None)
                if item is not None:
                    self.selected=('element',ident)
                    self.multi_selected.clear()
                    self.marquee_start=None
                    self.marquee_end=None
                    origin=item.get('annotation_offsets',{}).get(key,[0,0])
                    self.dragging={'mode':'annotation','id':ident,'key':key,
                                   'start':self._point(e),'origin':list(origin),
                                   'changed':False}
                    self._update_properties()
                    self.redraw()
                    return
            hit=self._hit(e)
            current_multi=set(self.multi_selected)
            current_selected=self.selected
            current_group=set(current_multi)
            if current_selected: current_group.add(current_selected)
            self.marquee_start=None
            self.marquee_end=None
            self.dragging=None
            # Si se pulsa sobre un objeto ya dentro de la selección múltiple,
            # se conserva el grupo y se prepara el arrastre conjunto.
            if hit and hit in current_group and len(current_group)>1:
                self.selected=hit
                self.multi_selected=current_group-{hit}
                self.dragging={'mode':'group','items':current_group,'start':(x,y),'changed':False,'prev':(0,0)}
                self._update_properties(); self.redraw(); return
            self.selected=hit
            self.multi_selected.clear()
            if hit and hit[0]=='element':
                el=self._selected_el()
                self.dragging={'mode':'single','id':el['id'],'start':(x,y),'origin':(el['x'],el['y']),'changed':False}
            elif hit and hit[0]=='wire':
                # El cable se traslada como objeto completo manteniendo su forma.
                wire=next((w for w in self.doc['wires'] if w['id']==hit[1]),None)
                if wire is not None:
                    self.dragging={'mode':'wire','id':wire['id'],
                                   'start':(x,y), 'origin':deepcopy(wire['points']),
                                   'changed':False}
            elif hit is None:
                # El botón izquierdo sobre el fondo mueve la vista ampliada.
                # Nunca cambia el dibujo ni crea un recuadro accidental.
                self.dragging={'mode':'pan','changed':False}
                self.canvas.scan_mark(e.x,e.y)
                self.canvas.configure(cursor='fleur')
            self._update_properties()
            self.redraw()
            return
        if not self._in_page(self._point(e)):
            return
        if self.tool in ('wire','wire_straight','wire_rectangle'):
            self._last_cursor=self._point(e)
            a,b=self._wire_xy(*self._last_cursor)
            a=max(GRID,min(PAGE_W-GRID,a))
            b=max(GRID,min(PAGE_H-GRID,b))
            if self.pending_wire is None:
                self.pending_wire=(a,b)
                self._status_var.set('Cable: selecciona el punto final · ESC para cancelar')
            else:
                try:
                    if self.tool=='wire_straight':
                        wire=make_straight_wire(self.pending_wire,(a,b))
                    elif self.tool=='wire_rectangle':
                        wire=make_rectangle_wire(self.pending_wire,(a,b))
                    else:
                        wire=make_wire(self.pending_wire,(a,b),self.horizontal_first)
                except ValueError:
                    self._status_var.set('Selecciona otro punto final (el rectángulo necesita ancho y alto).')
                else:
                    self._history()
                    self.doc['wires'].append(wire)
                    self.pending_wire=None
                    self._changed()
            self.redraw()
            return
        if self.tool=='text':
            result=self._text_dialog()
            if result:
                value,family,size=result
                self._history()
                self.doc['elements'].append(make_text(x,y,value,family,size))
                self._changed()
            return
        if self.tool=='image':
            if self._pending_image is not None:
                prepared=self._pending_image
                self._history()
                self.doc['elements'].append(make_image(x,y,**prepared))
                self._pending_image=None
                self.selected=('element',self.doc['elements'][-1]['id'])
                self._changed()
                self._set_tool('select')
            return
        if self.tool in SYMBOL_NAMES:
            kind=self.tool
            n=1
            prefix=DEFAULT_REFS.get(kind,'')
            existing={el.get('label','') for el in self.doc['elements']}
            if prefix:
                while f'{prefix}{n}' in existing:n+=1
                label=f'{prefix}{n}'
            else:label=''
            self._history()
            if kind=='selector_multi':
                count=self._selector_positions
                extent=round((count-1)*20*self.doc.get('drawing_scale',1.0))
                x=snap(max(GRID+extent+16,min(PAGE_W-GRID-extent-16,x)))
                y=snap(max(100,min(PAGE_H-100,y)))
                el=make_symbol(kind,x,y,label,selector_positions=count,
                               draw_scale=self.doc.get('drawing_scale',1.0))
            elif kind=='plc_module':
                a,b=self._plc_config
                template=make_symbol(kind,x,y,label,plc_inputs=a,plc_outputs=b,
                                     draw_scale=self.doc.get('drawing_scale',1.0))
                geo=plc_geometry(template)
                factor=template.get('draw_scale',1.0)
                x=min(max(GRID-geo['left']*factor,x),PAGE_W-GRID-geo['right']*factor)
                y=min(max(GRID-(geo['top']-30)*factor,y),PAGE_H-GRID-(geo['bottom']+30)*factor)
                x,y=snap(x),snap(y)
                el=make_symbol(kind,x,y,label,plc_inputs=a,plc_outputs=b,
                               draw_scale=self.doc.get('drawing_scale',1.0))
                el['plc_brand']=self._plc_brand
                el['plc_model']=self._plc_model
            else:
                el=make_symbol(kind,x,y,label,draw_scale=self.doc.get('drawing_scale',1.0))
            self.doc['elements'].append(el)
            self.selected=('element',el['id'])
            self._changed()
    def on_canvas_drag(self,e):
        if self.tool=='select_box' and self.marquee_start is not None:
            self.marquee_end=self._point(e)
            x1,y1=self._xy(*self.marquee_start)
            x2,y2=self._xy(*self.marquee_end)
            box=self.canvas.find_withtag('selection-marquee')
            if box:
                self.canvas.coords(box[-1],x1,y1,x2,y2)
            else:
                self.canvas.create_rectangle(x1,y1,x2,y2,outline=TEAL,
                    fill='#dff7f3',stipple='gray25',dash=(5,3),width=1.5,
                    tags=('selection-marquee',))
            return 'break'
        if self.tool!='select': return
        if self.dragging and self.dragging.get('mode')=='pan':
            if self.zoom_percent>100:
                self.canvas.scan_dragto(e.x,e.y,gain=1)
            return 'break'
        if self.marquee_start is not None:
            self.marquee_end=self._point(e)
            self.redraw()
            return
        if not self.dragging:return
        d=self.dragging
        if d.get('mode')=='annotation':
            item=next((i for i in self.doc['elements'] if i['id']==d['id']),None)
            if item is None:return
            px,py=self._point(e)
            startx,starty=d['start']
            # Movimiento libre, sin ajuste a rejilla; los puertos no cambian.
            ddx,ddy=_rotate(px-startx,py-starty,-item.get('rotation',0))
            factor=float(item.get('draw_scale',1.0))
            position=[round(d['origin'][0]+ddx/factor),round(d['origin'][1]+ddy/factor)]
            current=item.get('annotation_offsets',{}).get(d['key'],[0,0])
            if position!=current:
                if not d['changed']:
                    self._history();d['changed']=True
                offsets=item.setdefault('annotation_offsets',{})
                if position==[0,0]:
                    offsets.pop(d['key'],None)
                    if not offsets:item.pop('annotation_offsets',None)
                else:
                    offsets[d['key']]=position
                self.redraw()
            return
        if d.get('mode')=='wire':
            x,y=self._page_point(e)
            dx=x-d['start'][0];dy=y-d['start'][1]
            # Calcular desplazamiento desde la posición inicial, sin acumular
            # errores por sucesivos eventos de ratón.
            origin=d['origin']
            current=next((w for w in self.doc['wires'] if w['id']==d['id']),None)
            if current is None:return
            minx=min(p[0] for p in origin);maxx=max(p[0] for p in origin)
            miny=min(p[1] for p in origin);maxy=max(p[1] for p in origin)
            dx=int(snap(max(GRID-minx,min(PAGE_W-GRID-maxx,dx))))
            dy=int(snap(max(GRID-miny,min(PAGE_H-GRID-maxy,dy))))
            shifted=[[px+dx,py+dy] for px,py in origin]
            if current['points']!=shifted:
                if not d['changed']:
                    self._history();d['changed']=True
                current['points']=shifted
                self.redraw()
            return
        if d.get('mode')=='group':
            x,y=self._page_point(e)
            raw_dx=snap(x-d['start'][0]); raw_dy=snap(y-d['start'][1])
            step_dx=raw_dx-d['prev'][0]; step_dy=raw_dy-d['prev'][1]
            if step_dx==0 and step_dy==0:return
            bounds=self._group_bounds(d['items'])
            if bounds is None:return
            minx,miny,maxx,maxy=bounds
            step_dx=max(GRID-minx,min(PAGE_W-GRID-maxx,step_dx))
            step_dy=max(GRID-miny,min(PAGE_H-GRID-maxy,step_dy))
            if step_dx==0 and step_dy==0:return
            if not d['changed']:
                self._history(); d['changed']=True
            # Primero mover cables seleccionados para que los extremos ya no
            # coincidan con los puertos antiguos y no se dupliquen ajustes.
            for typ,ident in d['items']:
                if typ!='wire': continue
                wire=next((w for w in self.doc['wires'] if w['id']==ident),None)
                if wire is not None:
                    move_wire(self.doc,ident,step_dx,step_dy)
            for typ,ident in d['items']:
                if typ!='element': continue
                el=next((item for item in self.doc['elements'] if item['id']==ident),None)
                if el is not None:
                    move_element(self.doc,ident,el['x']+step_dx,el['y']+step_dy)
            d['prev']=(d['prev'][0]+step_dx,d['prev'][1]+step_dy)
            self.redraw()
            return
        x,y=self._page_point(e)
        dx,dy=x-d['start'][0],y-d['start'][1]
        new_x=max(GRID,min(PAGE_W-GRID,d['origin'][0]+dx))
        new_y=max(GRID,min(PAGE_H-GRID,d['origin'][1]+dy))
        el=self._selected_el()
        if el and (el['x'],el['y'])!=(new_x,new_y):
            if not d['changed']:
                self._history()
                d['changed']=True
            move_element(self.doc,d['id'],new_x,new_y)
            self.redraw()
    def on_canvas_up(self,e):
        if self.dragging and self.dragging.get('mode')=='pan':
            self.dragging=None
            self.canvas.configure(cursor='arrow')
            return 'break'
        was_area_tool=self.tool=='select_box'
        if self.marquee_start is not None:
            ex,ey=self._point(e)
            sx,sy=self.marquee_start
            self.marquee_start=None
            self.marquee_end=None
            if abs(ex-sx)*self.zoom>=5 and abs(ey-sy)*self.zoom>=5:
                left,right=sorted((sx,ex));top,bottom=sorted((sy,ey))
                picked=self._objects_in_area(left,top,right,bottom)
                if len(picked)==1:
                    self.selected=next(iter(picked));self.multi_selected.clear()
                else:
                    self.selected=None;self.multi_selected=picked
            else:
                self.selected=None;self.multi_selected.clear()
            self._update_properties()
            self.redraw()
        if self.dragging and self.dragging['changed']:self._changed()
        self.dragging=None
        if was_area_tool:
            # Mantener la selección y habilitar el arrastre del grupo.
            self._set_tool('select')
            self._update_properties()
        return 'break'

    def on_canvas_double(self,e):
        if self.tool!='select':return
        hit=self._hit(e)
        if hit and hit[0]=='element':
            self.selected=hit
            self._update_properties()
            self.edit_selected_dialog()

    def on_motion(self,e):
        x,y=self._point(e)
        self._last_cursor=(x,y)
        if self.tool=='select' and not self.dragging:
            # En espacio vacío se indica que se puede desplazar la vista.
            can_pan=self.zoom_percent>100 and self._hit(e) is None
            self.canvas.configure(cursor='fleur' if can_pan or self._hit_annotation(e) else 'arrow')
        if self.tool in ('wire','wire_straight','wire_rectangle'):self._draw_wire_overlay()

    def on_mousewheel(self,e):
        # La rueda controla SIEMPRE el zoom (sin necesidad de Ctrl).
        # Windows usa delta=120 por paso; en X11 se reciben Button-4/5.
        delta=getattr(e,'delta',0)
        if not delta and getattr(e,'num',0) in (4,5):
            delta=120 if e.num==4 else -120
        if not delta:return 'break'
        if self.dragging is not None or self.marquee_start is not None:return 'break'
        steps=min(8,max(1,round(abs(delta)/120)))
        factor=1.12**steps
        zoom=self.zoom_percent*(factor if delta>0 else 1/factor)
        self.set_zoom(zoom,anchor=(e.x,e.y))
        return 'break'

    def _text_dialog(self,item=None):
        """Fuente y tamaño del texto, también al editar mediante doble clic."""
        popup=tk.Toplevel(self.root)
        popup.title('Editar texto' if item else 'Añadir texto')
        popup.transient(self.root)
        popup.configure(bg='#f8fbfd')
        popup.resizable(False,False)
        frame=tk.Frame(popup,padx=16,pady=14,bg='#f8fbfd');frame.pack()
        tk.Label(frame,text='Texto',bg='#f8fbfd',fg=INK).grid(row=0,column=0,columnspan=2,sticky='w')
        txt=tk.Entry(frame,width=43,font=(FONT,11));txt.grid(row=1,column=0,columnspan=2,sticky='ew',pady=(3,12))
        txt.insert(0,item.get('label','') if item else '')
        tk.Label(frame,text='Fuente',bg='#f8fbfd',fg=INK).grid(row=2,column=0,sticky='w')
        tk.Label(frame,text='Tamaño',bg='#f8fbfd',fg=INK).grid(row=2,column=1,sticky='w')
        families=set(tkfont.families(self.root))
        common=['Arial','Calibri','Segoe UI','Times New Roman','Courier New','DejaVu Sans','Liberation Sans']
        options=list(dict.fromkeys(common+[f for f in sorted(families) if f and not f.startswith('@')]))
        font_var=tk.StringVar(value=(item.get('font_family','Arial') if item else 'Arial'))
        combo=ttk.Combobox(frame,textvariable=font_var,values=options,width=29)
        combo.grid(row=3,column=0,sticky='w',pady=(3,13),padx=(0,12))
        size_var=tk.StringVar(value=str(item.get('font_size',14) if item else 14))
        spin=tk.Spinbox(frame,from_=8,to=72,textvariable=size_var,width=7,
                        font=(FONT,10),justify='center')
        spin.grid(row=3,column=1,sticky='w',pady=(3,13))
        result=[]
        def accept(event=None):
            value=txt.get()[:240]
            family=font_var.get().strip()
            try:size=int(size_var.get())
            except ValueError:size=0
            if not value.strip():
                messagebox.showwarning('Texto','Escribe algún texto.',parent=popup);return
            if len(family)>60 or not family or any(ord(c)<32 for c in family) or not (8<=size<=72):
                messagebox.showwarning('Texto','Selecciona una fuente y tamaño entre 8 y 72.',parent=popup);return
            result.append((value,family,size));popup.destroy()
        actions=tk.Frame(frame,bg='#f8fbfd');actions.grid(row=4,column=0,columnspan=2,sticky='e')
        tk.Button(actions,text='Cancelar',command=popup.destroy).pack(side='left',padx=4)
        tk.Button(actions,text='Aceptar',command=accept,bg=TEAL,fg='white').pack(side='left')
        popup.bind('<Escape>',lambda e:popup.destroy())
        popup.bind('<Return>',accept)
        popup.protocol('WM_DELETE_WINDOW',popup.destroy)
        txt.focus_set();popup.grab_set();self.root.wait_window(popup)
        return result[0] if result else None

    def insert_image_dialog(self):
        """Selecciona una imagen local y activa su colocación con un clic."""
        path=filedialog.askopenfilename(parent=self.root,title='Insertar imagen',
            filetypes=[('Imágenes','*.png *.gif *.jpg *.jpeg'),('PNG','*.png'),('GIF','*.gif'),('JPEG','*.jpg *.jpeg')])
        if not path:return
        try:
            raw=Path(path).read_bytes()
            if len(raw)>4500000:raise ValueError('El archivo supera 4,5 MB.')
            suffix=Path(path).suffix.lower()
            fmt={'.png':'png','.gif':'gif','.jpg':'jpeg','.jpeg':'jpeg'}.get(suffix)
            if fmt not in ('png','gif','jpeg'):raise ValueError('Formato no admitido.')
            try:
                from PIL import Image
                with Image.open(io.BytesIO(raw)) as im:
                    iw,ih=im.size
                    if iw*ih>25000000 or iw>8000 or ih>8000:
                        raise ValueError('La imagen supera el tamaño máximo admitido (25 megapíxeles).')
                    im.load()
                    # Todos se convierten a PNG para que Tkinter pueda mostrarlos
                    # incluso si el programa se abre después sin Pillow.
                    if fmt=='jpeg':
                        buffer=io.BytesIO();im.convert('RGBA').save(buffer,format='PNG')
                        raw=buffer.getvalue();fmt='png'
            except ImportError:
                if fmt=='jpeg':raise ValueError('Para JPG/JPEG instala Pillow (pip install pillow). PNG y GIF no lo necesitan.')
                preview=tk.PhotoImage(data=base64.b64encode(raw).decode('ascii'))
                iw,ih=preview.width(),preview.height()
            if iw>12000 or ih>12000 or iw<=0 or ih<=0:
                raise ValueError('Las dimensiones de imagen no son válidas.')
            scale=min(1,280/iw,200/ih)
            width=max(1,round(iw*scale));height=max(1,round(ih*scale))
            encoded=base64.b64encode(raw).decode('ascii')
            payload={'encoded':encoded,'format':fmt,'width':width,'height':height}
            make_image(120,120,**payload) # validar antes de entrar en modo de colocar
        except Exception as err:
            messagebox.showerror('Insertar imagen',str(err),parent=self.root);return
        self._pending_image=payload
        self._set_tool('image')
        self.canvas.configure(cursor='crosshair')

    def _draw_image(self,item):
        """Imagen en segundo plano; referencias Tk conservadas hasta el redraw siguiente."""
        try:
            data=base64.b64decode(item['image_data'])
            w=max(1,round(item['width']*self.zoom))
            h=max(1,round(item['height']*self.zoom))
            try:
                from PIL import Image,ImageTk
                im=Image.open(io.BytesIO(data)).convert('RGBA')
                im.thumbnail((w,h),Image.Resampling.LANCZOS)
                photo=ImageTk.PhotoImage(im,master=self.root)
            except ImportError:
                photo=tk.PhotoImage(data=item['image_data'],master=self.root)
                factor=max(1,math.ceil(max(photo.width()/w,photo.height()/h)))
                if factor>1:photo=photo.subsample(factor,factor)
            self._image_refs.append(photo)
            self.canvas.create_image(*self._xy(item['x'],item['y']),image=photo,
                anchor='center',tags=('drawing',f'element:{item["id"]}'))
        except (OSError,ValueError,tk.TclError):
            self.canvas.create_text(*self._xy(item['x'],item['y']),text='[Imagen no disponible]',
                 fill='#ab2534',tags=('drawing',f'element:{item["id"]}'))

    def _edit_plc_signal_dialog(self,item):
        """Edición independiente de dirección (I0.0) y tipo (DI)."""
        dialog=tk.Toplevel(self.root)
        dialog.title('Editar señal de PLC')
        dialog.transient(self.root)
        dialog.resizable(False,False)
        dialog.configure(bg='#f8fbfd')
        pane=tk.Frame(dialog,padx=18,pady=14,bg='#f8fbfd')
        pane.pack(fill='both',expand=True)
        tk.Label(pane,text='Dirección / canal (por ejemplo I0.0)',bg='#f8fbfd',fg=INK).pack(anchor='w')
        addr=tk.Entry(pane,width=28,font=(FONT,11))
        addr.insert(0,item.get('label',''))
        addr.pack(fill='x',pady=(3,12))
        tk.Label(pane,text='Descripción (por ejemplo DI)',bg='#f8fbfd',fg=INK).pack(anchor='w')
        signal=tk.Entry(pane,width=28,font=(FONT,11))
        signal.insert(0,item.get('signal_type',''))
        signal.pack(fill='x',pady=(3,12))
        buttons=tk.Frame(pane,bg='#f8fbfd');buttons.pack(anchor='e')
        def accept():
            a,b=addr.get().strip(),signal.get().strip()
            if len(a)>240 or len(b)>32 or any(ord(c)<32 for c in a+b):
                messagebox.showwarning('Señal PLC','El contenido no es válido.',parent=dialog)
                return
            if (a,b)!=(item.get('label',''),item.get('signal_type','')):
                self._history()
                item['label']=a
                item['signal_type']=b
                self._changed()
            dialog.destroy()
        tk.Button(buttons,text='Cancelar',command=dialog.destroy).pack(side='left',padx=4)
        tk.Button(buttons,text='Guardar',command=accept,bg=TEAL,fg='white').pack(side='left')
        dialog.bind('<Escape>',lambda e:dialog.destroy())
        dialog.protocol('WM_DELETE_WINDOW',dialog.destroy)
        addr.focus_set();dialog.grab_set();self.root.wait_window(dialog)

    def _edit_image_dialog(self,item):
        answer=simpledialog.askinteger('Editar imagen','Anchura en el plano (mantiene proporción):',
                    parent=self.root,initialvalue=item['width'],minvalue=10,maxvalue=2000)
        if answer is None or answer==item['width']:return
        nw=answer;nh=max(1,round(item['height']*nw/item['width']))
        if nh>2000:
            messagebox.showwarning('Imagen','La altura excede el límite.',parent=self.root);return
        self._history();item['width']=nw;item['height']=nh;self._changed()

    def _raster_photo(self, key, factory):
        """Reuse high-DPI antialiased bitmaps across redraws and drags."""
        if key in self._symbol_cache:
            result=self._symbol_cache.pop(key)
            self._symbol_cache[key]=result
            return result
        result=factory()
        if result is None:return None
        img,left,top=result
        photo=quality_render.to_tk(img)
        entry=(photo,left,top)
        self._symbol_cache[key]=entry
        while len(self._symbol_cache)>220:
            self._symbol_cache.popitem(last=False)
        return entry

    def _draw_quality_symbol(self, shapes, tags, color):
        if not shapes:return
        key=('body',round(self.zoom,5),color,repr(shapes))
        result=self._raster_photo(key,lambda:quality_render.symbol_bitmap(shapes,self.zoom,color))
        if result is None:
            for shape in shapes:self._draw_shape(shape,tags,color)
            return
        photo,xx,yy=result
        self._quality_images.append(photo)
        self.canvas.create_image(self._offset_x+xx,self._offset_y+yy,image=photo,
                                 anchor='nw',tags=tags)

    def _draw_quality_label(self, shape, tags):
        key=('label',round(self.zoom,5),repr(shape))
        result=self._raster_photo(key,lambda:quality_render.label_bitmap(shape,self.zoom))
        if result is None:
            self._draw_shape(shape,tags)
            return
        photo,xx,yy=result
        self._quality_images.append(photo)
        self.canvas.create_image(self._offset_x+xx,self._offset_y+yy,image=photo,
                                 anchor='nw',tags=tags)

    def _draw_shape(self,shape,tags=(), color=INK,width=2):
        typ=shape[0]
        if typ in ('line','dashline'):
            _,x1,y1,x2,y2=shape
            self.canvas.create_line(*self._xy(x1,y1),*self._xy(x2,y2),fill=color,
                     width=max(1.0,1.55*self.zoom),capstyle='round',tags=tags,
                     dash=(4,3) if typ=='dashline' else ())
        elif typ in ('polygon','filledpolygon'):
            points=[]
            for x,y in shape[1]:points.extend(self._xy(x,y))
            self.canvas.create_polygon(points,fill=color if typ=='filledpolygon' else 'white',outline=color,
                      width=max(1.0,1.55*self.zoom),tags=tags)
        elif typ in ('dot','circle'):
            _,x,y,r=shape;px,py=self._xy(x,y);r*=self.zoom
            self.canvas.create_oval(px-r,py-r,px+r,py+r,
                   fill=color if typ=='dot' else 'white',outline=color,
                   width=max(1.0,1.55*self.zoom),tags=tags)
        elif typ in ('text','textcenter','textend'):
            _,x,y,text,size,fg,*family=shape
            self.canvas.create_text(*self._xy(x,y),text=text,anchor='center' if typ=='textcenter' else 'e' if typ=='textend' else 'w',
                     fill=fg,font=(family[0] if family else FONT,max(5,round(size*self.zoom))),tags=tags)

    def redraw(self):
        if not hasattr(self,'canvas'):return
        cv=self.canvas
        cv.delete('all')
        # Ocultar scrollbars cuando cabe TODA la hoja aumenta el área útil.
        show_scrollbars=self.zoom_percent>100
        if self._scrollbars_visible != show_scrollbars:
            self._scrollbars_visible=show_scrollbars
            if show_scrollbars:
                self._xbar.grid(row=1,column=0,sticky='ew')
                self._ybar.grid(row=0,column=1,sticky='ns')
            else:
                self._xbar.grid_remove()
                self._ybar.grid_remove()
        cw=max(1,cv.winfo_width())
        ch=max(1,cv.winfo_height())
        # El papel A4 apaisado debe ocupar el máximo a 100%, sin deformarse.
        # PAGE_H=900 sigue siendo el límite de edición de proyectos antiguos;
        # el borde físico de 297:210 tiene altura 905,05 en estas unidades.
        paper_h=paper_height(PAGE_W)
        fit=min(max(1,cw-8)/PAGE_W,max(1,ch-8)/paper_h)
        self.zoom=fit*self.zoom_percent/100.0
        width_px=PAGE_W*self.zoom
        height_px=paper_h*self.zoom
        self._offset_x=max(0.0,(cw-width_px)/2)
        self._offset_y=max(0.0,(ch-height_px)/2)
        cv.configure(scrollregion=(0,0,max(cw,width_px+8),max(ch,height_px+8)))
        x0,y0=self._xy(0,0)
        x1,y1=self._xy(PAGE_W,paper_h)
        cv.create_rectangle(x0+3,y0+3,x1+3,y1+3,fill='#d5dfe8',outline='')
        cv.create_rectangle(x0,y0,x1,y1,fill='white',outline='#bacbd7',width=1)
        # Visual guide every 20 units at 100%, fine 10-unit grid at high zoom.
        # Magnetic snapping always uses the exact 10-unit geometry.
        visual_grid=GRID if self.zoom_percent>=145 else GRID*2
        for x in range(0,PAGE_W+1,visual_grid):
            for y in range(0,PAGE_H+1,visual_grid):
                px,py=self._xy(x,y)
                cv.create_oval(px-.7,py-.7,px+.7,py+.7,fill='#dee6eb',outline='')
        self._draw_sheet()
        self._image_refs=[]
        self._quality_images=[]

        for item in self.doc['elements']:
            if item['kind']=='image':self._draw_image(item)
        for wire in self.doc['wires']:
            sel=self.selected==('wire',wire['id']) or ('wire',wire['id']) in self.multi_selected
            points=[]
            for px,py in wire['points']:points.extend(self._xy(px,py))
            color=TEAL if sel else INK
            stroke=max(1.0,1.65*self.zoom)
            cv.create_line(points,fill=color,width=stroke,
                         capstyle='round',joinstyle='round',tags=('drawing',f'wire:{wire["id"]}'))
            if sel:
                for a,b in (wire['points'][0],wire['points'][-1]):
                    xp,yp=self._xy(a,b)
                    cv.create_oval(xp-4,yp-4,xp+4,yp+4,fill=TEAL,outline='white',tags=('drawing',f'wire:{wire["id"]}'))
        for item in self.doc['elements']:
            selected=self.selected==('element',item['id']) or ('element',item['id']) in self.multi_selected
            tags=('drawing',f'element:{item["id"]}')
            if selected:
                xp,yp=self._xy(item['x'],item['y'])
                if item['kind']=='image':
                    hw=item['width']*self.zoom/2;hh=item['height']*self.zoom/2
                    box=(xp-hw-3,yp-hh-3,xp+hw+3,yp+hh+3)
                elif item['kind']=='plc_module':
                    pts=port_positions(item)
                    geo=plc_geometry(item)
                    factor=item.get('draw_scale',1.0)
                    left=min([item['x']+geo['left']*factor]+[xx for xx,yy in pts]);right=max([item['x']+geo['right']*factor]+[xx for xx,yy in pts])
                    top=min([item['y']+geo['top']*factor]+[yy for xx,yy in pts])
                    bottom=max(item['y']+geo['bottom']*factor,max(yy for xx,yy in pts))
                    x1,y1=self._xy(left-8,top-8);x2,y2=self._xy(right+8,bottom+8)
                    box=(x1,y1,x2,y2)
                elif item['kind']=='selector_multi':
                    # Cubrir todas las posiciones, no solo el centro del mando.
                    pts=port_positions(item)
                    x1,y1=self._xy(min(a for a,b in pts)-16,min(b for a,b in pts)-14)
                    x2,y2=self._xy(max(a for a,b in pts)+16,max(b for a,b in pts)+14)
                    box=(x1,y1,x2,y2)
                elif item['kind']=='breaker_4p':
                    # Marco de selección según sus ocho bornes (no cortar los extremos).
                    pts=port_positions(item)
                    x1,y1=self._xy(min(a for a,b in pts)-35,min(b for a,b in pts)-10)
                    x2,y2=self._xy(max(a for a,b in pts)+20,max(b for a,b in pts)+10)
                    box=(x1,y1,x2,y2)
                else:
                    radius=46*self.zoom*item.get('draw_scale',1.0) if item['kind']!='text' else 12
                    box=(xp-radius*.5,yp-radius,xp+radius*1.6,yp+radius)
                cv.create_rectangle(*box,outline='#81d5d1',dash=(4,3),width=1.5,tags=tags)
            if item['kind']!='image':
                body=symbol_shapes(item,include_annotations=False)
                ink=TEAL if selected else INK
                if quality_render.AVAILABLE:
                    self._draw_quality_symbol(body,tags,ink)
                else:
                    for shape in body:self._draw_shape(shape,tags,ink)
                for key,shape in annotation_positions(item):
                    labeltags=tags+(f'annotation:{item["id"]}:{key}',)
                    if quality_render.AVAILABLE:
                        self._draw_quality_label(shape,labeltags)
                    else:
                        self._draw_shape(shape,labeltags,ink)
        for x,y in junction_points(self.doc):
            px,py=self._xy(x,y)
            radius=max(2.6,3.7*self.zoom)
            cv.create_oval(px-radius,py-radius,px+radius,py+radius,
                fill=INK,outline=INK,tags=('junction-dot',))
        self._draw_wire_overlay()
        if self.tool=='select_box' and self.marquee_start is not None and self.marquee_end is not None:
            x1,y1=self._xy(*self.marquee_start)
            x2,y2=self._xy(*self.marquee_end)
            cv.create_rectangle(x1,y1,x2,y2,outline=TEAL,fill='#dff7f3',
                 stipple='gray25',dash=(5,3),width=1.5,tags=('selection-marquee',))

    def _draw_wire_overlay(self):
        """Rastro de cable y señal visual al llegar a puerto o cable existente."""
        cv=self.canvas
        cv.delete('wire-overlay')
        if self.tool not in ('wire','wire_straight','wire_rectangle'):return
        x,y=self._last_cursor
        if not self._in_page((x,y)):return
        target=self._wire_target(x,y)
        end=target['point'] if target else (snap(x),snap(y))
        if self.pending_wire is not None:
            if end!=self.pending_wire:
                try:
                    if self.tool=='wire_straight':
                        preview=make_straight_wire(self.pending_wire,end)
                    elif self.tool=='wire_rectangle':
                        preview=make_rectangle_wire(self.pending_wire,end)
                    else:
                        preview=make_wire(self.pending_wire,end,self.horizontal_first)
                    coords=[]
                    for a,b in preview['points']:coords.extend(self._xy(a,b))
                    cv.create_line(coords,fill=TEAL,width=max(1.0,1.65*self.zoom),dash=(6,4),
                        capstyle='round',joinstyle='round',tags=('wire-overlay',))
                except ValueError:pass
            sx,sy=self._xy(*self.pending_wire)
            cv.create_oval(sx-5,sy-5,sx+5,sy+5,fill=TEAL,outline='white',
                           tags=('wire-overlay',))
        if target is not None:
            px,py=self._xy(*end)
            cv.create_oval(px-9,py-9,px+9,py+9,fill='',outline='#0eaf67',
                         width=2.7,tags=('wire-overlay',))
            cv.create_oval(px-3.5,py-3.5,px+3.5,py+3.5,fill='#0eaf67',outline='',
                           tags=('wire-overlay',))


    def _draw_sheet(self):
        cv=self.canvas
        # Zonas impresas: A-H en la parte superior e inferior, 1-5 en ambos
        # laterales. La misma geometría se exporta a SVG (futuro PDF A4).
        geo=guide_geometry(PAGE_W)
        for a,b,c,d in (geo['outer'],geo['inner']):
            cv.create_rectangle(*self._xy(a,b),*self._xy(c,d),
                                outline=GREEN,width=max(1,1.4*self.zoom))
        for a,b,c,d in geo['lines']:
            cv.create_line(*self._xy(a,b),*self._xy(c,d),
                           fill=GREEN,width=max(1,1.4*self.zoom))
        for x,y,label in geo['labels']:
            cv.create_text(*self._xy(x,y),text=label,fill=GREEN,
                           font=(FONT,max(9,round(12*self.zoom)),'bold'))
        self._draw_title_block()

    def _draw_title_block(self):
        cv=self.canvas
        box=title_block_geometry()
        left,top,right,bottom=box['outer']
        cv.create_rectangle(*self._xy(left,top),*self._xy(right,bottom),
                            fill='white',outline='#a6c6d1',width=1.2)
        cv.create_line(*self._xy(left,box['header_y']),*self._xy(right,box['header_y']),fill='#a6c6d1')
        cv.create_line(*self._xy(box['divider_x'],top),*self._xy(box['divider_x'],bottom),fill='#a6c6d1')
        title=self.doc['title']
        title_size=15
        while title_size>9:
            f=tkfont.Font(family=FONT,size=max(7,int(title_size*self.zoom)),weight='bold')
            if f.measure(title)<=box['title_max_width']*self.zoom:break
            title_size-=1
        for text,x,y,size,fg,bold in [
            ('ELECTRICAL WORK  ·  TÍTULO DEL PLANO',box['left_center_x'],box['header_center_y'],10,MUTED,False),
            (title,box['left_center_x'],box['value_center_y'],title_size,INK,True),
            ('HOJA',box['right_center_x'],box['header_center_y'],10,MUTED,False),
            (f'{self.sheet_index+1}/{len(self.project["sheets"])}',box['right_center_x'],box['value_center_y'],13,INK,True)]:
            cx,cy=self._xy(x,y)
            cv.create_text(cx,cy,text=text,anchor='center',fill=fg,
                  font=(FONT,max(7,int(size*self.zoom)), 'bold' if bold else 'normal'))

    def _selected_el(self):
        if not self.selected or self.selected[0]!='element':return None
        return next((e for e in self.doc['elements'] if e['id']==self.selected[1]),None)

    def _update_properties(self):
        """Sin panel lateral: acciones activas según la selección actual."""
        if self.multi_selected:
            self._selection_var.set(f'{len(self.multi_selected)} objetos seleccionados')
            self._prop_var.set('')
            for btn in (self.edit_button,self.rotate_left_button,
                        self.rotate_right_button,self.duplicate_button):
                btn.config(state='disabled')
            self.delete_button.config(state='normal')
            return
        el=self._selected_el()
        if el:
            desc=('Texto libre' if el['kind']=='text' else SYMBOL_NAMES.get(el['kind'],'?'))
            self._selection_var.set(f'{desc} · {el.get("label", "")}')
            self._prop_var.set(el.get('label',''))
            self.edit_button.config(state='normal')
            state='normal' if el['kind'] not in ('text','image') else 'disabled'
            self.rotate_left_button.config(state=state)
            self.rotate_right_button.config(state=state)
            self.duplicate_button.config(state='normal')
            self.delete_button.config(state='normal')
        elif self.selected and self.selected[0]=='wire':
            self._selection_var.set('Cable')
            self._prop_var.set('')
            for btn in (self.edit_button,self.rotate_left_button,self.rotate_right_button):
                btn.config(state='disabled')
            for btn in (self.duplicate_button,self.delete_button):btn.config(state='normal')
        else:
            self._selection_var.set('Sin selección')
            self._prop_var.set('')
            for btn in (self.edit_button,self.rotate_left_button,self.rotate_right_button,
                        self.duplicate_button,self.delete_button):
                btn.config(state='disabled')

    def _history(self):
        self.undo_stack.append(deepcopy(self.doc))
        if len(self.undo_stack)>60:self.undo_stack.pop(0)
        self.redo_stack.clear()

    def _changed(self):
        self._sync_current_sheet()
        self.dirty=True
        self._update_caption()
        self._update_properties()
        self.redraw()

    def _update_caption(self):
        name=os.path.basename(self.filepath) if self.filepath else 'Sin guardar'
        self.root.title(f'Electrical Work · {name}{" *" if self.dirty else ""} · COMPACTO V0.5.2')

    def return_to_pointer(self,event=None):
        """Esc siempre desactiva la herramienta de dibujo actual."""
        self.cancel_pending()
        self._set_tool('select')
        return 'break'

    def cancel_pending(self):
        self.pending_wire=None
        self.dragging=None
        self._status_var.set('Acción cancelada')
        self.redraw()

    def undo(self):
        if not self.undo_stack:return
        self.redo_stack.append(deepcopy(self.doc))
        self.doc=self.undo_stack.pop()
        self.selected=None
        self.multi_selected.clear()
        self.marquee_start=None
        self.marquee_end=None
        self.pending_wire=None
        self._title_var.set(self.doc['title'])
        self._changed()
        self._status_var.set('Deshacer')

    def redo(self):
        if not self.redo_stack:return
        self.undo_stack.append(deepcopy(self.doc))
        self.doc=self.redo_stack.pop()
        self.selected=None
        self.multi_selected.clear()
        self.marquee_start=None
        self.marquee_end=None
        self.pending_wire=None
        self._title_var.set(self.doc['title'])
        self._changed()
        self._status_var.set('Rehacer')

    def delete_selected(self):
        selected=set(self.multi_selected)
        if self.selected:selected.add(self.selected)
        if not selected:return
        self._history()
        self.doc['elements']=[el for el in self.doc['elements']
                              if ('element',el['id']) not in selected]
        self.doc['wires']=[wire for wire in self.doc['wires']
                           if ('wire',wire['id']) not in selected]
        self.selected=None
        self.multi_selected.clear()
        self.marquee_start=None
        self.marquee_end=None
        self._changed()

    def duplicate_selected(self):
        """Duplica el objeto seleccionado desplazándolo dos pasos de rejilla."""
        if not self.selected:return
        typ,ident=self.selected
        collection=self.doc['elements'] if typ=='element' else self.doc['wires']
        source=next((item for item in collection if item['id']==ident),None)
        if source is None:return
        offset=GRID*2
        if typ=='element':
            # No crear figuras fuera de la hoja.
            if source['x']+offset>PAGE_W-GRID or source['y']+offset>PAGE_H-GRID:
                messagebox.showwarning('Duplicar','No hay espacio hacia abajo y a la derecha.',parent=self.root)
                return
            copy_item=deepcopy(source)
            copy_item.update(id=new_id(),x=source['x']+offset,y=source['y']+offset)
        else:
            pts=source['points']
            if any(x+offset>PAGE_W-GRID or y+offset>PAGE_H-GRID for x,y in pts):
                messagebox.showwarning('Duplicar','No hay espacio hacia abajo y a la derecha.',parent=self.root)
                return
            copy_item={'id':new_id(),'points':[[x+offset,y+offset] for x,y in pts]}
            if source.get('mode'):copy_item['mode']=source['mode']
        self._history()
        collection.append(copy_item)
        self.selected=(typ,copy_item['id'])
        self._changed()

    def rotate_selected(self,direction=1):
        el=self._selected_el()
        if not el or el['kind'] in ('text','image'):return
        self._history()
        rotate_element(self.doc,el['id'],direction)
        self._changed()

    def apply_property(self):
        el=self._selected_el()
        if not el:return
        value=self._prop_var.get().strip()
        if value!=el.get('label',''):
            self._history()
            el['label']=value[:240]
            self._changed()

    def _edit_directional_terminal(self,item):
        popup=tk.Toplevel(self.root)
        popup.title('Editar borne direccional')
        popup.configure(bg='#f8fbfd')
        popup.transient(self.root);popup.resizable(False,False)
        frame=tk.Frame(popup,bg='#f8fbfd',padx=18,pady=15)
        frame.pack(fill='both',expand=True)
        fields=(('Referencia (opcional)','label',100),
                ('Dirección de página (ej.: Pag 2/2A)','direction_page',80))
        entries=[]
        for row,(caption,key,limit) in enumerate(fields):
            tk.Label(frame,text=caption,bg='#f8fbfd',fg=INK,
                     font=(FONT,10)).grid(row=row*2,column=0,sticky='w',pady=(3,3))
            field=tk.Entry(frame,width=36,font=(FONT,11),fg=INK)
            field.insert(0,item.get(key,''))
            field.grid(row=row*2+1,column=0,sticky='ew',pady=(0,8))
            entries.append((key,field,limit))
        actions=tk.Frame(frame,bg='#f8fbfd')
        actions.grid(row=len(fields)*2,column=0,sticky='e',pady=(8,0))
        def confirm(event=None):
            values={key:field.get().strip() for key,field,limit in entries}
            if any(len(values[key])>limit or any(ord(ch)<32 for ch in values[key])
                   for key,field,limit in entries):
                messagebox.showwarning('Borne direccional','Revisa la longitud de los textos.',parent=popup)
                return
            if any(item.get(key,'')!=value for key,value in values.items()) or 'direction_text' in item:
                self._history();item.update(values)
                item.pop('direction_text',None)
                self._changed()
            popup.destroy()
        tk.Button(actions,text='Cancelar',command=popup.destroy,bg='#edf3f7',
                  fg=INK,relief='flat',padx=10,pady=6).pack(side='left',padx=4)
        tk.Button(actions,text='Guardar',command=confirm,bg=TEAL,fg='white',
                  relief='flat',padx=12,pady=6).pack(side='left')
        popup.bind('<Return>',confirm)
        popup.bind('<Escape>',lambda e:popup.destroy())
        popup.protocol('WM_DELETE_WINDOW',popup.destroy)
        popup.update_idletasks()
        px=self.root.winfo_rootx()+(self.root.winfo_width()-popup.winfo_width())//2
        py=self.root.winfo_rooty()+(self.root.winfo_height()-popup.winfo_height())//2
        popup.geometry(f'+{max(0,px)}+{max(0,py)}')
        entries[0][1].focus_set()
        popup.grab_set();self.root.wait_window(popup)

    def _edit_selector_dialog(self,el):
        """Edita cantidad, referencia y numeración opcional de cada posición."""
        popup=tk.Toplevel(self.root)
        popup.title('Editar selector multiposición')
        popup.transient(self.root)
        popup.configure(bg='#f8fbfd')
        popup.resizable(False,False)
        frame=tk.Frame(popup,bg='#f8fbfd',padx=18,pady=13)
        frame.pack(fill='both',expand=True)
        tk.Label(frame,text='Número de posiciones (2–12)',bg='#f8fbfd',fg=INK).grid(row=0,column=0,sticky='w')
        count_var=tk.StringVar(value=str(el['selector_positions']))
        counter=tk.Spinbox(frame,from_=2,to=MAX_SELECTOR_POSITIONS,width=10,
                           textvariable=count_var,justify='center')
        counter.grid(row=0,column=1,sticky='ew',pady=5)
        tk.Label(frame,text='Referencia',bg='#f8fbfd',fg=INK).grid(row=1,column=0,sticky='w')
        reference=tk.Entry(frame,width=20)
        reference.insert(0,el.get('label',''))
        reference.grid(row=1,column=1,sticky='ew',pady=5)
        tk.Label(frame,text='Bornes opcionales',bg='#f8fbfd',fg=INK,
                 font=(FONT,10,'bold')).grid(row=2,column=0,columnspan=2,sticky='w',pady=(8,4))
        holder=tk.Frame(frame,bg='#f8fbfd')
        holder.grid(row=3,column=0,columnspan=2,sticky='ew')
        initial=get_terminal_labels(el)
        edits={i:initial[i] for i in range(el['selector_positions'])}
        common=[initial[-1]]
        def rebuild(*args):
            try: count=int(count_var.get())
            except ValueError:return
            if not 2<=count<=MAX_SELECTOR_POSITIONS:return
            old_count=rebuild.count
            for i,ent in getattr(rebuild,'fields',{}).items():
                try: value=ent.get()
                except tk.TclError:continue
                if i==old_count:common[0]=value
                else:edits[i]=value
            for child in holder.winfo_children():child.destroy()
            fields={}
            for i in range(count+1):
                name=(f'Posición {i+1}' if i<count else 'Común')
                tk.Label(holder,text=name,bg='#f8fbfd',fg=INK).grid(row=i,column=0,sticky='w',padx=(0,12),pady=2)
                field=tk.Entry(holder,width=15)
                # El borne común mantiene su valor al variar N.
                val=common[0] if i==count else edits.get(i,'')
                field.insert(0,val)
                field.grid(row=i,column=1,sticky='ew',pady=2)
                fields[i]=field
            rebuild.fields=fields
            rebuild.count=count
        rebuild.fields={}
        rebuild.count=el['selector_positions']
        count_var.trace_add('write',rebuild)
        rebuild()
        bar=tk.Frame(frame,bg='#f8fbfd');bar.grid(row=4,column=0,columnspan=2,sticky='e',pady=(12,0))
        def accept(event=None):
            try:
                count=int(count_var.get())
                if not 2<=count<=MAX_SELECTOR_POSITIONS:raise ValueError
            except ValueError:
                messagebox.showwarning('Selector','Número de posiciones inválido.',parent=popup)
                return
            label=reference.get()[:240]
            values=[rebuild.fields[i].get().strip() for i in range(count+1)]
            if any(len(v)>12 or '\n' in v or '\r' in v for v in values):
                messagebox.showwarning('Selector','Cada borne admite un máximo de 12 caracteres.',parent=popup)
                return
            count_changed=count!=el['selector_positions']
            if count_changed:
                old_ports=set(port_positions(el))
                if any(tuple(w['points'][i]) in old_ports for w in self.doc['wires'] for i in (0,-1)):
                    messagebox.showwarning('Selector',
                        'Desconecta primero los cables del selector antes de cambiar las posiciones.',parent=popup)
                    return
                # Sin pérdida silenciosa de números al reducir el selector.
                if count<el['selector_positions'] and any(v for v in initial[count:el['selector_positions']]):
                    if not messagebox.askyesno('Selector','Las posiciones retiradas tienen numeraciones. ¿Continuar?',parent=popup):return
            if count_changed or label!=el.get('label','') or values!=get_terminal_labels(el):
                self._history()
                if count_changed:
                    extent=round((count-1)*20*el.get('draw_scale',1.0))
                    # Si se amplía junto al borde, desplazar el selector entero
                    # para mantener los contactos dentro del área imprimible.
                    el['x']=snap(max(GRID+extent+16,min(PAGE_W-GRID-extent-16,el['x'])))
                el['selector_positions']=count
                el['label']=label
                if any(values):el['terminal_labels']=values
                else:el.pop('terminal_labels',None)
                # descartar offsets que ya no correspondan a bornes existentes
                if count_changed and 'annotation_offsets' in el:
                    old_count=len(initial)-1
                    old_offsets=el['annotation_offsets']
                    new_offsets={}
                    for key,point in old_offsets.items():
                        if key==f'terminal:{old_count}':
                            new_offsets[f'terminal:{count}']=point
                        elif not key.startswith('terminal:'):
                            new_offsets[key]=point
                        elif key[9:].isdigit() and int(key[9:])<count:
                            new_offsets[key]=point
                    if new_offsets:el['annotation_offsets']=new_offsets
                    else:el.pop('annotation_offsets',None)
                self._changed()
            popup.destroy()
        tk.Button(bar,text='Cancelar',command=popup.destroy,bg='#e9eff5',relief='flat',padx=10,pady=6).pack(side='left',padx=4)
        tk.Button(bar,text='Guardar',command=accept,bg=TEAL,fg='white',relief='flat',padx=10,pady=6).pack(side='left')
        popup.bind('<Escape>',lambda e:popup.destroy())
        popup.bind('<Return>',accept)
        popup.protocol('WM_DELETE_WINDOW',popup.destroy)
        popup.update_idletasks()
        x=self.root.winfo_rootx()+(self.root.winfo_width()-popup.winfo_width())//2
        y=self.root.winfo_rooty()+(self.root.winfo_height()-popup.winfo_height())//2
        popup.geometry(f'+{max(0,x)}+{max(0,y)}')
        reference.focus_set()
        popup.grab_set();self.root.wait_window(popup)

    def edit_selected_dialog(self):
        el=self._selected_el()
        if not el:return
        names=terminal_label_names(el)
        if el['kind'] in ('directional_terminal','directional_terminal_in'):
            self._edit_directional_terminal(el)
            return
        if el['kind']=='selector_multi':
            self._edit_selector_dialog(el)
            return
        if el['kind']=='plc_module':
            chosen=self._plc_counts_dialog((el['plc_inputs'],el['plc_outputs'],el.get('plc_brand',''),el.get('plc_model','')))
            if chosen is not None:
                counts_changed=(chosen[0],chosen[1])!=(el['plc_inputs'],el['plc_outputs'])
                texts_changed=(chosen[2],chosen[3])!=(el.get('plc_brand',''),el.get('plc_model',''))
                if counts_changed:
                    old_ports=set(port_positions(el))
                    wired=any(tuple(w['points'][i]) in old_ports for w in self.doc['wires'] for i in (0,-1))
                    if wired:
                        messagebox.showwarning('PLC','Antes de cambiar el número de entradas/salidas, desconecta los cables del PLC. Así evitamos conexiones incorrectas.', parent=self.root)
                        return
                if counts_changed or texts_changed:
                    self._history()
                    el.update(plc_inputs=chosen[0],plc_outputs=chosen[1],plc_brand=chosen[2],plc_model=chosen[3])
                    if counts_changed:
                        geom=plc_geometry(el)
                        factor=el.get('draw_scale',1.0)
                        el['x']=snap(max(GRID-geom['left']*factor,
                                         min(PAGE_W-GRID-geom['right']*factor,el['x'])))
                        el['y']=snap(max(GRID-geom['top']*factor,
                                         min(PAGE_H-GRID-geom['bottom']*factor,el['y'])))
                    self._changed()
            return
        if el['kind'] in ('plc_input','plc_output'):
            self._edit_plc_signal_dialog(el)
            return
        if el['kind']=='image':
            self._edit_image_dialog(el)
            return
        if not names:
            if el['kind']=='text':
                result=self._text_dialog(el)
                if result:
                    value,family,size=result
                    if (value,family,size)!=(el.get('label',''),el.get('font_family','Arial'),el.get('font_size',14)):
                        self._history()
                        el.update(label=value,font_family=family,font_size=size)
                        self._changed()
                return
            answer=simpledialog.askstring('Editar referencia / texto','Texto:',
                              initialvalue=el.get('label',''),parent=self.root)
            if answer is not None and answer!=el.get('label',''):
                self._history();el['label']=answer[:240];self._changed()
            return
        popup=tk.Toplevel(self.root)
        popup.title('Editar bobina' if el['kind'].startswith('coil') else 'Editar contacto')
        popup.transient(self.root)
        popup.configure(bg='#f8fbfd')
        popup.resizable(False,False)
        frame=tk.Frame(popup,bg='#f8fbfd',padx=18,pady=14)
        frame.pack(fill='both',expand=True)
        tk.Label(frame,text='Referencia del contacto',bg='#f8fbfd',fg=INK,
                 font=(FONT,10,'bold')).grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,5))
        label_entry=tk.Entry(frame,width=28,font=(FONT,11),fg=INK)
        label_entry.insert(0,el.get('label',''))
        label_entry.grid(row=1,column=0,columnspan=2,sticky='ew',pady=(0,10))
        tk.Label(frame,text='Numeración de bornes (opcional)',bg='#f8fbfd',fg=INK,
                 font=(FONT,10,'bold')).grid(row=2,column=0,columnspan=2,sticky='w',pady=(0,6))
        entries=[]
        for index,(name,value) in enumerate(zip(names,get_terminal_labels(el)),start=3):
            tk.Label(frame,text=name,bg='#f8fbfd',fg=INK,
                     font=(FONT,9)).grid(row=index,column=0,sticky='w',padx=(0,12),pady=3)
            field=tk.Entry(frame,width=12,font=(FONT,10),fg=INK)
            field.insert(0,value)
            field.grid(row=index,column=1,sticky='ew',pady=3)
            entries.append(field)
        hintrow=3+len(entries)
        tk.Label(frame,text=('Ejemplo: A1 / A2' if el['kind'].startswith('coil') else 'Ejemplo: NA 13/14 · NC 21/22 · térmico 95/96'),
                 font=(FONT,8),fg=MUTED,bg='#f8fbfd').grid(row=hintrow,column=0,columnspan=2,
                                                         sticky='w',pady=(8,10))
        actionbar=tk.Frame(frame,bg='#f8fbfd')
        actionbar.grid(row=hintrow+1,column=0,columnspan=2,sticky='e')
        def confirm(event=None):
            label=label_entry.get()[:240]
            values=[entry.get().strip() for entry in entries]
            if any(len(v)>12 or '\n' in v or '\r' in v for v in values):
                messagebox.showwarning('Numeración','Cada borne admite hasta 12 caracteres.',parent=popup)
                return
            original=get_terminal_labels(el)
            if label!=el.get('label','') or values!=original:
                self._history()
                el['label']=label
                if any(values):el['terminal_labels']=values
                else:el.pop('terminal_labels',None)
                self._changed()
            popup.destroy()
        tk.Button(actionbar,text='Cancelar',command=popup.destroy,font=(FONT,9),
                  relief='flat',bg='#e9eff5',padx=10,pady=6).pack(side='left',padx=4)
        tk.Button(actionbar,text='Guardar',command=confirm,font=(FONT,9,'bold'),
                  relief='flat',fg='white',bg=TEAL,padx=12,pady=6).pack(side='left')
        popup.bind('<Escape>',lambda e:popup.destroy())
        popup.bind('<Return>',confirm)
        popup.protocol('WM_DELETE_WINDOW',popup.destroy)
        popup.update_idletasks()
        cx=self.root.winfo_rootx()+(self.root.winfo_width()-popup.winfo_reqwidth())//2
        cy=self.root.winfo_rooty()+(self.root.winfo_height()-popup.winfo_reqheight())//2
        popup.geometry(f'+{max(0,cx)}+{max(0,cy)}')
        label_entry.focus_set()
        popup.grab_set()
        self.root.wait_window(popup)

    def edit_title_dialog(self):
        answer=simpledialog.askstring('Título del plano','Nuevo título:',
                    initialvalue=self.doc['title'],parent=self.root)
        if answer is not None:
            self._title_var.set(answer)
            self.apply_title()

    def apply_title(self):
        title=self._title_var.get().strip()[:200]
        if not title:
            messagebox.showwarning('Título vacío','Escribe un título para el plano.',parent=self.root)
            return
        if title!=self.doc['title']:
            self._history();self.doc['title']=title;self._changed();self._refresh_sheets()

    @staticmethod
    def _zoom_text(percent):
        return f'{percent:g}'

    def apply_zoom_entry(self,event=None):
        """Permite zoom numérico libre en % (1 a 1000), sin escalones."""
        typed=self._zoom_var.get().strip().replace('%','').replace(',','.')
        try:
            value=float(typed)
        except ValueError:
            self.root.bell()
            self._zoom_var.set(self._zoom_text(self.zoom_percent))
            return 'break'
        if not (1<=value<=1000):
            self.root.bell()
            self._zoom_var.set(self._zoom_text(self.zoom_percent))
            return 'break'
        self.set_zoom(value)
        self.canvas.focus_set()
        return 'break'

    def set_zoom(self,percent,anchor=None):
        """Zoom de 1–1000 %: al girar la rueda conserva el punto bajo el cursor.

        100 % ajusta la hoja completa al espacio disponible. Los controles
        numéricos y +/- conservan el centro visible, sin alterar el proyecto.
        """
        percent=max(1.0,min(1000.0,float(percent)))
        cv=self.canvas
        if anchor is None:
            anchor=(cv.winfo_width()/2,cv.winfo_height()/2)
        ax,ay=anchor
        before=((cv.canvasx(ax)-self._offset_x)/self.zoom,
                (cv.canvasy(ay)-self._offset_y)/self.zoom)
        self.zoom_percent=round(percent,3)
        self._zoom_var.set(self._zoom_text(self.zoom_percent))
        self.redraw()
        if self.zoom_percent<=100:
            cv.xview_moveto(0)
            cv.yview_moveto(0)
            return
        # canvasx/canvasy incorporan el desplazamiento de las barras.
        # xview_moveto recibe una fracción del scrollregion completo.
        target_x,target_y=self._xy(*before)
        width=max(cv.winfo_width(),PAGE_W*self.zoom+8)
        height=max(cv.winfo_height(),paper_height(PAGE_W)*self.zoom+8)
        cv.xview_moveto(max(0,(target_x-ax)/width))
        cv.yview_moveto(max(0,(target_y-ay)/height))


    def _sync_current_sheet(self):
        if hasattr(self,'project'):
            self.project['sheets'][self.sheet_index]=self.doc

    def _refresh_sheets(self):
        if not hasattr(self,'sheet_picker'):return
        values=[f'{i+1:03d}  {sheet["title"]}' for i,sheet in enumerate(self.project['sheets'])]
        self.sheet_picker.configure(values=values)
        self._sheet_var.set(values[self.sheet_index])
        self.sheet_prev_button.configure(state='normal' if self.sheet_index>0 else 'disabled')
        self.sheet_next_button.configure(state='normal' if self.sheet_index<len(values)-1 else 'disabled')
        self.sheet_delete_button.configure(state='normal' if len(values)>1 else 'disabled')
        self.sheet_move_up_button.configure(state='normal' if self.sheet_index>0 else 'disabled')
        self.sheet_move_down_button.configure(state='normal' if self.sheet_index<len(values)-1 else 'disabled')
        if hasattr(self,'sheet_menu'):
            self.sheet_menu.entryconfigure(1,state='normal' if len(values)>1 else 'disabled')
            self.sheet_menu.entryconfigure(4,state='normal' if self.sheet_index>0 else 'disabled')
            self.sheet_menu.entryconfigure(5,state='normal' if self.sheet_index<len(values)-1 else 'disabled')

    def _choose_sheet(self,event=None):
        index=self.sheet_picker.current()
        if index>=0:self.switch_sheet(index)

    def switch_sheet(self,index):
        if index<0 or index>=len(self.project['sheets']):
            self._refresh_sheets();return False
        if index==self.sheet_index:
            self._refresh_sheets();return True
        self._sync_current_sheet()
        self._close_contact_popup()
        self.sheet_index=index
        self.doc=self.project['sheets'][index]
        self.selected=None
        self.multi_selected.clear()
        self.marquee_start=self.marquee_end=None
        self.pending_wire=None
        self.dragging=None
        # El historial es independiente por hoja para impedir deshacer en otra.
        self.undo_stack.clear();self.redo_stack.clear()
        self._title_var.set(self.doc['title'])
        self._refresh_sheets();self._update_properties();self.redraw()
        return True

    def move_sheet(self,direction):
        """Sube/baja la hoja sin cambiar su contenido ni sus IDs."""
        if direction not in (-1,1):return False
        new_index=self.sheet_index+direction
        if not (0<=new_index<len(self.project['sheets'])):
            self._refresh_sheets();return False
        self._sync_current_sheet()
        sheets=self.project['sheets']
        old_index=self.sheet_index
        sheets[old_index],sheets[new_index]=sheets[new_index],sheets[old_index]
        self.sheet_index=new_index
        self.doc=sheets[new_index]
        # Actualizar las asignaciones numéricas de hojas manuales. El texto
        # libre, como 2A o 2/2A, se conserva sin reinterpretarlo.
        for record in self.project.get('documentation_manual',[]):
            ref=record.get('sheets','')
            if isinstance(ref,str) and ref.isascii() and ref.isdecimal() and len(ref)<=3:
                number=int(ref)
                if number in (old_index+1,new_index+1):
                    remap=(new_index+1 if number==old_index+1 else old_index+1)
                    record['sheets']=str(remap).zfill(len(ref))
        # La documentación automática identifica cada aparato por su ID,
        # y calcula de nuevo el número de hoja en el orden actualizado.
        self.pending_wire=None
        self.dragging=None
        self.dirty=True
        self._title_var.set(self.doc['title'])
        self._update_caption();self._refresh_sheets()
        self._update_properties();self.redraw()
        return True

    def add_sheet(self):
        if len(self.project['sheets'])>=MAX_SHEETS:
            messagebox.showwarning('Límite de hojas','Máximo de 1000 hojas por proyecto.',parent=self.root)
            return False
        self._sync_current_sheet()
        num=len(self.project['sheets'])+1
        doc=new_document();doc['title']=f'Hoja {num}'
        doc['drawing_scale']=self.doc.get('drawing_scale',1.0)
        self.project['sheets'].append(doc)
        self.switch_sheet(num-1)
        self.dirty=True;self._update_caption()
        return True

    def delete_sheet(self):
        if len(self.project['sheets'])==1:return False
        num=self.sheet_index+1
        if not messagebox.askyesno('Eliminar hoja',
                f'¿Eliminar la hoja {num} y todos sus elementos? Esta acción no se puede deshacer.',
                parent=self.root):return False
        del self.project['sheets'][self.sheet_index]
        self.sheet_index=min(self.sheet_index,len(self.project['sheets'])-1)
        self.doc=self.project['sheets'][self.sheet_index]
        self.selected=None;self.multi_selected.clear()
        self.marquee_start=self.marquee_end=None
        self.pending_wire=None;self.dragging=None
        self.undo_stack.clear();self.redo_stack.clear()
        self._title_var.set(self.doc['title'])
        self.dirty=True;self._refresh_sheets();self._update_caption()
        self._update_properties();self.redraw()
        return True

    def rename_sheet(self):
        value=simpledialog.askstring('Renombrar hoja','Nombre de la hoja:',
              initialvalue=self.doc['title'],parent=self.root)
        if value is None:return False
        name=value.strip()
        if not name or len(name)>200:
            messagebox.showwarning('Nombre de hoja','Escribe un nombre de 1 a 200 caracteres.',parent=self.root)
            return False
        if name!=self.doc['title']:
            self._history();self.doc['title']=name;self._title_var.set(name)
            self._changed();self._refresh_sheets()
        return True

    def rename_project(self):
        value=simpledialog.askstring('Nombre del proyecto','Nombre del proyecto:',
              initialvalue=self.project['title'],parent=self.root)
        if value is None:return False
        name=value.strip()
        if not name or len(name)>200:
            messagebox.showwarning('Nombre de proyecto','Escribe un nombre de 1 a 200 caracteres.',parent=self.root)
            return False
        if name!=self.project['title']:
            self.project['title']=name;self.dirty=True;self._update_caption()
        return True

    def _reset_project(self,project,file=None):
        self.project=project
        self.sheet_index=0
        self.doc=project['sheets'][0]
        self.filepath=file
        self.dirty=False
        self.selected=None
        self.multi_selected.clear()
        self.marquee_start=self.marquee_end=None
        self.pending_wire=None;self.dragging=None
        self.undo_stack.clear();self.redo_stack.clear()
        self._title_var.set(self.doc['title'])
        self._refresh_sheets();self._update_properties()
        self._update_caption();self.redraw()

    def _confirm_discard(self):
        if not self.dirty:return True
        choice=messagebox.askyesnocancel('Cambios sin guardar',
               'El plano tiene cambios sin guardar. ¿Quieres guardarlos primero?',parent=self.root)
        if choice is None:return False
        if choice:return self.save_file()
        return True

    def _reset_document(self,doc,file=None):
        # Compatibilidad con utilidades/pruebas que cargan una hoja V1.
        self._reset_project(project_from_document(doc),file)

    def new_file(self):
        if not self._confirm_discard():return
        self._reset_project(new_project())
        self._status_var.set('Nuevo plano creado')

    def open_file(self):
        if not self._confirm_discard():return
        name=filedialog.askopenfilename(parent=self.root,title='Abrir proyecto',
                 filetypes=[('Electrical Work','*.ework'),('JSON','*.json')])
        if not name:return
        try:project=load_project(name)
        except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as ex:
            messagebox.showerror('Error al abrir',f'No se pudo abrir el proyecto:\n{ex}',parent=self.root)
            return
        self._reset_project(project,name)
        self._status_var.set('Proyecto abierto: '+os.path.basename(name))

    def save_as(self):
        name=filedialog.asksaveasfilename(parent=self.root,title='Guardar proyecto',
               defaultextension='.ework',filetypes=[('Electrical Work','*.ework')])
        if not name:return False
        return self._save_to(name)

    def _save_to(self,name):
        self._sync_current_sheet()
        try:save_project(self.project,name)
        except (OSError,ValueError) as ex:
            messagebox.showerror('Error al guardar',str(ex),parent=self.root)
            return False
        self.filepath=name
        self.dirty=False
        self._update_caption()
        self._status_var.set('Guardado: '+os.path.basename(name))
        return True

    def save_file(self):
        if not self.filepath:return self.save_as()
        return self._save_to(self.filepath)

    def open_documentation(self):
        """Documentación Excel-like: editar, añadir y quitar filas sin borrar el plano."""
        if self._documentation_window is not None:
            if self._documentation_window.winfo_exists():
                self._documentation_window.lift()
                self._documentation_window.focus_set()
                return
        self._sync_current_sheet()
        panel=tk.Toplevel(self.root)
        self._documentation_window=panel
        panel.title('Electrical Work · Documentación del proyecto')
        # Centrar la ventana en la pantalla, teniendo en cuenta resoluciones
        # pequeñas y evitando abrirla fuera del área visible.
        screen_width=panel.winfo_screenwidth()
        screen_height=panel.winfo_screenheight()
        width=min(1100,max(400,screen_width-80))
        height=min(670,max(350,screen_height-100))
        left=max(0,(screen_width-width)//2)
        top=max(0,(screen_height-height)//2)
        panel.geometry(f'{width}x{height}+{left}+{top}')
        panel.minsize(min(880,width),min(490,height))
        panel.configure(bg='#f8fbfd')
        panel.transient(self.root)
        bar=tk.Frame(panel,bg=NAVY,height=57)
        bar.pack(fill='x');bar.pack_propagate(False)
        tk.Label(bar,text='DOCUMENTACIÓN DEL ESQUEMA',font=(FONT,13,'bold'),
                 bg=NAVY,fg='white').pack(side='left',padx=18,pady=15)
        search_frame=tk.Frame(panel,bg='#f8fbfd')
        search_frame.pack(fill='x',padx=16,pady=(13,8))
        tk.Label(search_frame,text='Buscar:',bg='#f8fbfd',fg=INK,
                 font=(FONT,10)).pack(side='left')
        search_var=tk.StringVar()
        search=tk.Entry(search_frame,textvariable=search_var,font=(FONT,10),width=40)
        search.pack(side='left',padx=9,fill='x',expand=True)
        count_var=tk.StringVar()
        tk.Label(search_frame,textvariable=count_var,bg='#f8fbfd',fg=MUTED,
                 font=(FONT,9)).pack(side='right',padx=3)

        table_frame=tk.Frame(panel,bg='#f8fbfd')
        table_frame.pack(fill='both',expand=True,padx=16,pady=5)
        columns=('group','reference','description','sheets')
        tree=ttk.Treeview(table_frame,columns=columns,show='headings',selectmode='browse')
        tree.heading('group',text='Familia')
        tree.heading('reference',text='Referencia')
        tree.heading('description',text='Descripción (doble clic para editar)')
        tree.heading('sheets',text='Hoja')
        tree.column('group',width=170,minwidth=120,stretch=False)
        tree.column('reference',width=145,minwidth=95,stretch=False)
        tree.column('description',width=610,minwidth=280,stretch=True)
        tree.column('sheets',width=60,minwidth=50,stretch=False,anchor='center')
        scroll=tk.Scrollbar(table_frame,orient='vertical',command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side='left',fill='both',expand=True)
        scroll.pack(side='right',fill='y')
        edit_entry=[None]
        active_key=[None]

        def rows_by_key():
            return {row['key']:row for row in documentation_rows(self.project)}

        def mark_dirty():
            self.dirty=True
            self._update_caption()

        def refresh(*ignored):
            if edit_entry[0] is not None:return
            pattern=search_var.get().strip().casefold()
            selected=tree.selection()
            for item in tree.get_children():tree.delete(item)
            rows=documentation_rows(self.project)
            visible=0
            for record in rows:
                if pattern and pattern not in ' '.join(str(record[k])
                        for k in ('group','reference','description','sheets')).casefold():
                    continue
                tree.insert('',tk.END,iid=record['key'],
                    values=(record['group'],record['reference'],
                            record['description'],record['sheets']))
                visible+=1
            count_var.set(f'{visible} de {len(rows)} referencias')
            if selected and tree.exists(selected[0]):
                tree.selection_set(selected[0]);tree.focus(selected[0])

        def commit(event=None):
            if edit_entry[0] is None:return True
            editor=edit_entry[0]
            key=active_key[0]
            value=editor.get()
            row=rows_by_key().get(key)
            if row is None:
                edit_entry[0]=None;active_key[0]=None;editor.destroy();refresh()
                return False
            if value.strip()!=row['description']:
                try:
                    set_description(self.project,key,value)
                except ValueError as exc:
                    messagebox.showwarning('Descripción',str(exc),parent=panel)
                    editor.focus_set()
                    return False
                mark_dirty()
            edit_entry[0]=None
            active_key[0]=None
            editor.destroy()
            refresh()
            return True

        def cancel_edit(event=None):
            if edit_entry[0] is not None:
                widget=edit_entry[0]
                edit_entry[0]=None
                active_key[0]=None
                widget.destroy()
                refresh()

        def edit_selected(event=None):
            if not commit():return
            selection=tree.selection()
            if not selection:return
            key=selection[0]
            row=rows_by_key().get(key)
            if row is None:return
            tree.focus(key);tree.see(key)
            panel.update_idletasks()
            coords=tree.bbox(key,'#3')
            if not coords:return
            x,y,w,h=coords
            editor=tk.Entry(tree,font=(FONT,10),relief='solid',bd=1)
            editor.insert(0,row['description'])
            editor.place(x=x,y=y,width=max(w,80),height=max(h,25))
            editor.focus_set();editor.icursor('end')
            edit_entry[0]=editor
            active_key[0]=key
            editor.bind('<Return>',commit)
            editor.bind('<KP_Enter>',commit)
            editor.bind('<FocusOut>',commit)
            editor.bind('<Escape>',cancel_edit)

        def selected_record():
            selection=tree.selection()
            return rows_by_key().get(selection[0]) if selection else None

        def manual_dialog(record=None):
            window=tk.Toplevel(panel)
            window.title('Editar fila' if record else 'Añadir fila de documentación')
            window.transient(panel)
            window.configure(bg='#f8fbfd')
            window.resizable(False,False)
            holder=tk.Frame(window,bg='#f8fbfd',padx=20,pady=16)
            holder.pack(fill='both',expand=True)
            vars={}
            values={
                'group': record['group'] if record else '',
                'reference': record['reference'] if record else '',
                'description': record['description'] if record else '',
                'sheets': record['sheets'] if record else f'{self.sheet_index+1:03d}',
            }
            for n,(field,title) in enumerate((
                ('group','Familia'),('reference','Referencia'),
                ('description','Descripción'),('sheets','Hoja (opcional)'),
            )):
                tk.Label(holder,text=title,font=(FONT,10),bg='#f8fbfd',fg=INK).grid(
                    row=n*2,column=0,sticky='w',pady=(6,3))
                var=tk.StringVar(value=values[field]);vars[field]=var
                if field=='group':
                    entry=ttk.Combobox(holder,textvariable=var,state='normal',
                                       values=tuple(dict.fromkeys((*GROUPS,*(r['group'] for r in documentation_rows(self.project))))),width=38)
                else:
                    entry=tk.Entry(holder,textvariable=var,width=44,font=(FONT,10))
                entry.grid(row=n*2+1,column=0,sticky='ew',pady=(0,3))
            tk.Label(holder,text='Las filas manuales no crean componentes en el esquema.',
                bg='#f8fbfd',fg=MUTED,font=(FONT,9)).grid(row=8,column=0,sticky='w',pady=(10,8))
            answer=[None]
            buttons=tk.Frame(holder,bg='#f8fbfd');buttons.grid(row=9,column=0,sticky='e')
            def accept(event=None):
                answer[0]=tuple(vars[name].get() for name in ('group','reference','description','sheets'))
                try:
                    # La validación definitiva se realiza antes de cerrar el diálogo.
                    from documentation import _validate_text
                    _validate_text(answer[0][0],80,'Familia',required=True)
                    _validate_text(answer[0][1],100,'Referencia',required=True)
                    _validate_text(answer[0][2],600,'Descripción')
                    _validate_text(answer[0][3],30,'Hoja')
                except ValueError as error:
                    messagebox.showwarning('Fila de documentación',str(error),parent=window)
                    return
                window.destroy()
            tk.Button(buttons,text='Cancelar',command=window.destroy,font=(FONT,10),
                bg='#edf3f7',relief='flat',padx=10,pady=6).pack(side='left',padx=5)
            tk.Button(buttons,text='Guardar',command=accept,font=(FONT,10,'bold'),
                bg=TEAL,fg='white',relief='flat',padx=10,pady=6).pack(side='left')
            window.bind('<Escape>',lambda e:window.destroy())
            window.bind('<Return>',accept)
            window.grab_set()
            window.focus_set()
            window.wait_window()
            return answer[0]

        def add_row():
            if not commit():return
            values=manual_dialog()
            if values is None:return
            try:
                key=add_manual_row(self.project,*values)
            except ValueError as exc:
                messagebox.showwarning('Añadir fila',str(exc),parent=panel);return
            mark_dirty();refresh()
            if tree.exists(key):tree.selection_set(key);tree.focus(key);tree.see(key)

        def edit_manual_row():
            if not commit():return
            row=selected_record()
            if row is None:
                messagebox.showinfo('Editar fila','Selecciona una fila.',parent=panel);return
            if not row['manual']:
                messagebox.showinfo('Referencia del esquema',
                    'La familia y la referencia de esta fila proceden del dibujo. '
                    'Puedes cambiar su descripción o añadir una fila manual.',parent=panel)
                return
            values=manual_dialog(row)
            if values is None:return
            if values != (row['group'],row['reference'],row['description'],row['sheets']):
                try:update_manual_row(self.project,row['key'],*values)
                except ValueError as exc:
                    messagebox.showwarning('Editar fila',str(exc),parent=panel);return
                mark_dirty();refresh()

        def remove_row():
            if not commit():return
            row=selected_record()
            if row is None:
                messagebox.showinfo('Quitar fila','Selecciona una fila.',parent=panel);return
            detail=('Se quitará de la documentación. El elemento seguirá en el esquema.'
                    if not row['manual'] else 'Se eliminará esta fila manual.')
            if not messagebox.askyesno('Quitar de documentación',
                    f'¿Quitar {row["reference"]}?\n\n{detail}',parent=panel):return
            try:delete_documentation_row(self.project,row['key'])
            except ValueError as exc:
                messagebox.showwarning('Quitar fila',str(exc),parent=panel);return
            mark_dirty();refresh()

        def on_double(event):
            column=tree.identify_column(event.x)
            if column=='#3':edit_selected()
            elif column in ('#1','#2','#4'):
                if selected_record() and selected_record()['manual']:edit_manual_row()

        tree.bind('<Double-1>',on_double)
        tree.bind('<F2>',edit_selected)
        tree.bind('<Delete>',lambda e:remove_row())
        search_var.trace_add('write',refresh)

        controls=tk.Frame(panel,bg='#f8fbfd')
        controls.pack(fill='x',padx=16,pady=(6,8))
        self._btn(controls,'Añadir fila',add_row,bg=TEAL,fg='white',padx=10,pady=7).pack(side='left')
        self._btn(controls,'Editar descripción',edit_selected,bg='#edf3f7',fg=INK,padx=10,pady=7).pack(side='left',padx=4)
        self._btn(controls,'Editar fila',edit_manual_row,bg='#edf3f7',fg=INK,padx=10,pady=7).pack(side='left',padx=4)
        self._btn(controls,'Quitar fila',remove_row,bg='#faecee',fg='#8e3f48',padx=10,pady=7).pack(side='left',padx=4)

        export_controls=tk.Frame(panel,bg='#f8fbfd')
        export_controls.pack(fill='x',padx=16,pady=(0,8))
        def print_docs():
            if not commit():return
            filename=filedialog.asksaveasfilename(parent=panel,title='Exportar documentación PDF',
                       defaultextension='.pdf',filetypes=[('PDF A4','*.pdf')],
                       initialfile='Documentacion.pdf')
            if not filename:return
            try:count=export_project_pdf(self.project,filename,documentation_only=True)
            except (ValueError,OSError,RuntimeError) as exc:
                messagebox.showerror('Error PDF',str(exc),parent=panel);return
            messagebox.showinfo('Documentación exportada',
                f'PDF creado correctamente: {count} página(s).',parent=panel)
        self._btn(export_controls,'Exportar PDF',print_docs,bg='#edf3f7',fg=INK,padx=10,pady=7).pack(side='left')
        def export_csv():
            if not commit():return
            filename=filedialog.asksaveasfilename(parent=panel,
                title='Exportar documentación a Excel/CSV',
                defaultextension='.csv',filetypes=[('Archivo CSV para Excel','*.csv')],
                initialfile='Documentacion.csv')
            if not filename:return
            try:export_documentation_csv(self.project,filename)
            except (ValueError,OSError) as exc:
                messagebox.showerror('Error CSV',str(exc),parent=panel);return
            messagebox.showinfo('Tabla exportada','Archivo CSV creado para Excel.',parent=panel)
        self._btn(export_controls,'Exportar CSV',export_csv,bg='#edf3f7',fg=INK,padx=10,pady=7).pack(side='left',padx=5)
        def close():
            if commit():
                self._documentation_window=None
                panel.destroy()
        self._btn(export_controls,'Cerrar',close,bg='#edf3f7',fg=INK,padx=10,pady=7).pack(side='right')
        tk.Label(export_controls,text='Quitar fila no borra el símbolo. Añadir fila no altera el dibujo.',
            bg='#f8fbfd',fg=MUTED,font=(FONT,9)).pack(side='right',padx=12)
        panel.protocol('WM_DELETE_WINDOW',close)
        panel.bind('<Control-s>',lambda e:self.save_file() if commit() else None)
        refresh()

    def export_pdf_dialog(self):
        """PDF imprimible A4 apaisado: hoja actual, proyecto, con o sin tabla."""
        self._sync_current_sheet()
        popup=tk.Toplevel(self.root)
        popup.title('Exportar PDF A4')
        popup.transient(self.root)
        popup.resizable(False,False)
        popup.configure(bg='#f8fbfd')
        content=tk.Frame(popup,bg='#f8fbfd',padx=22,pady=18)
        content.pack(fill='both',expand=True)
        tk.Label(content,text='Exportar a PDF',font=(FONT,13,'bold'),bg='#f8fbfd',fg=INK).pack(anchor='w',pady=(0,12))
        mode=tk.StringVar(value='all' if len(self.project['sheets'])>1 else 'one')
        options=[('Hoja actual  ·  '+str(self.sheet_index+1).zfill(3),'one'),
                 ('Proyecto completo  ·  '+str(len(self.project['sheets']))+' hoja(s)','all')]
        for label,val in options:
            tk.Radiobutton(content,text=label,variable=mode,value=val,
                           bg='#f8fbfd',fg=INK,activebackground='#f8fbfd',font=(FONT,10)).pack(anchor='w',pady=4)
        include=tk.BooleanVar(value=False)
        tk.Checkbutton(content,text='Añadir documentación al final del PDF',
                       variable=include,bg='#f8fbfd',fg=INK,
                       activebackground='#f8fbfd',font=(FONT,10)).pack(anchor='w',pady=(13,10))
        tk.Label(content,text='Formato DIN A4 apaisado (297 × 210 mm).\nUn plano por página, sin deformar símbolos ni dibujos.',
                 justify='left',bg='#f8fbfd',fg=MUTED,font=(FONT,9)).pack(anchor='w',pady=(5,15))
        controls=tk.Frame(content,bg='#f8fbfd')
        controls.pack(fill='x')
        def make_pdf():
            selected_mode=mode.get()
            add_docs=include.get()
            popup.destroy()
            filename=filedialog.asksaveasfilename(parent=self.root,title='Guardar PDF A4',
                defaultextension='.pdf',filetypes=[('Documento PDF','*.pdf')],initialfile='Esquema.pdf')
            if not filename:return
            try:
                indexes=[self.sheet_index] if selected_mode=='one' else None
                total=export_project_pdf(self.project,filename,sheet_indices=indexes,
                                         include_documentation=add_docs)
            except (ValueError,OSError,RuntimeError) as exc:
                messagebox.showerror('Error al exportar PDF',str(exc),parent=self.root);return
            self._status_var.set('PDF exportado: '+os.path.basename(filename))
            messagebox.showinfo('PDF creado',f'PDF A4 guardado correctamente ({total} página(s)).',parent=self.root)
        self._btn(controls,'Cancelar',popup.destroy,bg='#edf3f7',fg=INK,padx=10,pady=7).pack(side='left')
        self._btn(controls,'Exportar PDF',make_pdf,bg=TEAL,fg='white',padx=10,pady=7).pack(side='right')
        popup.bind('<Escape>',lambda e:popup.destroy())
        popup.grab_set()
        popup.update_idletasks()
        popup.geometry(f'+{self.root.winfo_rootx()+200}+{self.root.winfo_rooty()+160}')

    def export_file(self):
        name=filedialog.asksaveasfilename(parent=self.root,title='Exportar dibujo SVG',
             defaultextension='.svg',filetypes=[('Gráfico vectorial SVG','*.svg')])
        if not name:return
        try:export_svg(self.doc,name,self.sheet_index+1,len(self.project['sheets']))
        except (OSError,ValueError) as ex:
            messagebox.showerror('Error al exportar',str(ex),parent=self.root)
            return
        self._status_var.set('SVG exportado: '+os.path.basename(name))
        messagebox.showinfo('Exportación correcta','Hoja actual exportada a SVG.\nPuedes abrirla en un navegador o en un editor vectorial.',parent=self.root)

    def on_close(self):
        if self._confirm_discard():
            self._close_contact_popup()
            self.root.destroy()


def main():
    root=tk.Tk()
    app=ElectricalWorkApp(root)
    if len(sys.argv)>1:
        try:app._reset_project(load_project(sys.argv[1]),sys.argv[1])
        except (ValueError,OSError,json.JSONDecodeError) as err:
            messagebox.showerror('Error al abrir',str(err),parent=root)
    root.mainloop()

if __name__=='__main__':main()
