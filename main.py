from unittest import result
from bottleneck import move_mean, move_median, move_sum
from scipy.signal import butter, filtfilt, find_peaks
from scipy.fft import fft, fftfreq
# from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt6 import QtCore, QtWidgets
from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError
import helperFunctions_UI
import numpy as np
import threading
import datetime
import asyncio
import struct
import time
import sys
import os
import struct   
import csv
from pywt import waverec

class mainWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):


        self.bleDevice        = "BionodeW"
        self.bleServiceUUID   = "80ea98d0-bf05-4d48-92e4-f16b33600320"
        self.bleCharUUID      = "91fd3072-5f44-4038-85d7-b807e11b5121"
        self.num_channels     = 1
        self.fs               = 1000 # Hz
        self.plot_refreshRate = 20 # Hz
        self.reconnectDelay   = 2 # sec

        if len(sys.argv) > 1:
            self.num_channels = int(sys.argv[1])
        if len(sys.argv) > 2:
            self.fs           = sys.argv[2]

        super(mainWidget, self).__init__(parent)
        self.setWindowTitle("DWT Compression Stream")
        self.pathSave_default = os.path.join('.','data_raw')
        self.displayPaused = False
        self.dataToDisplay = []
        self.recording = False
        self.displayIndex = 0
        self.stopStream = False

        if not(os.path.exists(self.pathSave_default)) and not(os.path.isdir(self.pathSave_default)):
            os.mkdir(self.pathSave_default)
            
        # Create the graphs
        self.graphLayout = QtWidgets.QGridLayout()
        self.graphicsViews = []
        self.plotItems = []
        self.plots = []
        # Create the processing options
        self.process_gb      = []
        self.filterL_l       = []
        self.filterL_t       = []
        self.filterH_l       = []
        self.filterH_t       = []
        self.filterOrder_s   = []
        self.psd_cb          = []
        self.abs_cb          = []
        self.zNormalize_cb   = []
        self.detectPeaks_cb  = []
        self.detectPeaksC_l  = []
        self.detectPeaksR_l  = []
        self.peakRate_cb     = []
        self.peakRate_l      = []
        self.peakHeight      = []
        self.peakThreshold   = []
        self.peakDistance    = []
        self.peakProminence  = []
        self.peakWidth       = []
        self.movingMean_cb   = []
        self.movingMean_t    = []
        self.movingMedian_cb = []
        self.movingMedian_t  = []
        self.movingRMS_cb    = []
        self.movingRMS_t     = []
        self.movingSum_cb    = []
        self.movingSum_t     = []
        self.processLayout   = []
        colors = [(200,200,0), (50,200,0), (100,200,200), (200,0,200)]
        for i in range(self.num_channels):
            graphicsView_data = helperFunctions_UI.makeGraphicsView()
            plotItem_data = graphicsView_data.getPlotItem()
            plotItem_data.setTitle(title='Channel '+str(i))
            plotItem_data.setLabel('left',text='Voltage', units='V')
            plotItem_data.showLabel('left',show=True)
            if i == (self.num_channels-1):
                plotItem_data.setLabel('bottom',text='Time',units='s')
            else:
                plotItem_data.setLabel('bottom')
            plotItem_data.showLabel('bottom',show=True)
            plotItem_data.showGrid(x=True,y=True)

            plot_data = plotItem_data.plot()
            plot_data.setPen(colors[i%len(colors)])

            graphicsView_freq = helperFunctions_UI.makeGraphicsView()
            plotItem_freq = graphicsView_freq.getPlotItem()
            plotItem_freq.setTitle(title='Channel '+str(i)+' PSD')
            plotItem_freq.setLabel('left',text='Magnitude', units='dB/Hz')
            plotItem_freq.showLabel('left',show=True)
            plotItem_freq.setLabel('bottom')
            plotItem_freq.showLabel('bottom',show=True)
            plotItem_freq.showGrid(x=False,y=True)
            plotItem_freq.setLogMode(x=False,y=True)

            plot_freq = plotItem_freq.plot()
            plot_freq.setPen(colors[i%len(colors)])

            graphicsView_data.setVisible(True)
            graphicsView_freq.setVisible(False)

            self.graphicsViews.append( [graphicsView_data, graphicsView_freq])
            self.plotItems.append( [plotItem_data, plotItem_freq])
            self.plots.append( [plot_data, plot_freq])
            self.graphLayout.addWidget(self.graphicsViews[i][0], i, 0)
            
        
            parent_gb       = helperFunctions_UI.makeGroupBox('Channel '+str(i))
            channel_t       = helperFunctions_UI.makeTextBox(parent_gb, text='[Optional Label]')
            filterL_l       = helperFunctions_UI.makeLabel('Filter Cutoffs  Low:', parent_gb)
            filterL_t       = helperFunctions_UI.makeTextBox(parent_gb)
            filterH_l       = helperFunctions_UI.makeLabel('  High:', parent_gb)
            filterH_t       = helperFunctions_UI.makeTextBox(parent_gb)
            filterOrder_s   = helperFunctions_UI.makeSliderBar(parent_gb, 1, 10, 1, initialValue=5)
            psd_cb          = helperFunctions_UI.makeCheckBox('Calculate PSD', parent_gb)
            abs_cb          = helperFunctions_UI.makeCheckBox('Absolute Value', parent_gb)
            zNormalize_cb   = helperFunctions_UI.makeCheckBox('Z-Score Normalize', parent_gb)
            movingMean_cb   = helperFunctions_UI.makeCheckBox('Moving Mean  window(ms):', parent_gb)
            movingMean_t    = helperFunctions_UI.makeTextBox(parent_gb)
            movingMedian_cb = helperFunctions_UI.makeCheckBox('Moving Median  window(ms):', parent_gb)
            movingMedian_t  = helperFunctions_UI.makeTextBox(parent_gb)
            movingRMS_cb    = helperFunctions_UI.makeCheckBox('Moving RMS  window(ms):', parent_gb)
            movingRMS_t     = helperFunctions_UI.makeTextBox(parent_gb)
            movingSum_cb    = helperFunctions_UI.makeCheckBox('Moving Sum  window(ms):', parent_gb)
            movingSum_t     = helperFunctions_UI.makeTextBox(parent_gb)

            placeholder_l   = helperFunctions_UI.makeLabel(' ',parent_gb)
            filterL_t.textChanged.connect( self.calculateFilterCoef)
            filterH_t.textChanged.connect( self.calculateFilterCoef)
            filterOrder_s.valueChanged.connect( self.calculateFilterCoef)
            abs_cb.stateChanged.connect( self.updateAbs)
            zNormalize_cb.stateChanged.connect( self.updateZNormalize)
            movingMean_cb.stateChanged.connect( self.calculateMovingMeanWindow)
            movingMean_t.textChanged.connect( self.calculateMovingMeanWindow)
            movingMedian_cb.stateChanged.connect( self.calculateMovingMedianWindow)
            movingMedian_t.textChanged.connect( self.calculateMovingMedianWindow)
            movingRMS_cb.stateChanged.connect( self.calculateMovingRMSWindow)
            movingRMS_t.textChanged.connect( self.calculateMovingRMSWindow)
            movingSum_cb.stateChanged.connect( self.calculateMovingSumWindow)
            movingSum_t.textChanged.connect( self.calculateMovingSumWindow)
            psd_cb.stateChanged.connect( self.updateFreq)

            channelLayout    = helperFunctions_UI.makeHorizontalLayout([channel_t])
            filterLayout     = helperFunctions_UI.makeHorizontalLayout([filterL_l,filterL_t,filterH_l,filterH_t])
            movingMeanLayout = helperFunctions_UI.makeHorizontalLayout([movingMean_cb,movingMean_t])
            movingMedianLayout = helperFunctions_UI.makeHorizontalLayout([movingMedian_cb,movingMedian_t])
            movingRMSLayout  = helperFunctions_UI.makeHorizontalLayout([movingRMS_cb,movingRMS_t])
            movingSumLayout  = helperFunctions_UI.makeHorizontalLayout([movingSum_cb,movingSum_t])
            processLayout = helperFunctions_UI.makeVerticalLayout([ channelLayout,
                                                                    filterLayout,
                                                                    filterOrder_s,
                                                                    abs_cb,
                                                                    zNormalize_cb,
                                                                    movingMeanLayout,
                                                                    movingMedianLayout,
                                                                    movingRMSLayout,
                                                                    movingSumLayout,
                                                                    psd_cb,
                                                                    ])
            placeholder_layout = helperFunctions_UI.makeVerticalLayout([placeholder_l])
            processLayout.addLayout(placeholder_layout,99)
            
            self.process_gb.append(parent_gb)
            self.filterL_t.append(filterL_t)
            self.filterH_t.append(filterH_t)
            self.filterOrder_s.append(filterOrder_s)
            self.psd_cb.append(psd_cb)
            self.abs_cb.append(abs_cb)
            self.zNormalize_cb.append(zNormalize_cb)
            self.movingMean_cb.append(movingMean_cb)
            self.movingMean_t.append(movingMean_t)
            self.movingMedian_cb.append(movingMedian_cb)
            self.movingMedian_t.append(movingMedian_t)
            self.movingRMS_cb.append(movingRMS_cb)
            self.movingRMS_t.append(movingRMS_t)
            self.movingSum_cb.append(movingSum_cb)
            self.movingSum_t.append(movingSum_t)
            self.processLayout.append(processLayout)

        self.processLayout  = helperFunctions_UI.makeVerticalLayout(self.processLayout)
        self.channelLayout  = helperFunctions_UI.makeHorizontalLayout([self.processLayout])
        self.channelLayout.addLayout(self.graphLayout, 99)

        # Metadata Layout
        self.metadata_gb    = helperFunctions_UI.makeGroupBox('Metadata')
        self.bleDevice_l     = helperFunctions_UI.makeLabel('Device', self.metadata_gb )
        self.bleDevice_t     = helperFunctions_UI.makeTextBox( self.metadata_gb)
        self.bleDevice_t.setText(self.bleDevice)
        self.connect_b      = helperFunctions_UI.makeButton("Connect", self.metadata_gb, enabled=True)
        self.connect_b.clicked.connect(self.stream)
        # self.voltageRail_dd = helperFunctions_UI.makeComboBox(self.metadata_gb, items=['0.1 V','0.2 V','0.5 V','1 V','2 V','5 V','10 V'])
        # self.voltageRail_dd.setCurrentIndex(5)
        # self.voltageRail_dd.currentIndexChanged.connect(self.initializeGraphing)
        # self.sampleRate_l   = helperFunctions_UI.makeLabel('Sample Rate', self.metadata_gb )
        # self.sampleRate_t   = helperFunctions_UI.makeTextBox( self.metadata_gb)
        # self.sampleRate_t.setText(str(int(self.fs)))
        # self.sampleRate_t.textChanged.connect(self.initializeGraphing)
        self.refreshRate_l  = helperFunctions_UI.makeLabel('Refresh Rate (Hz)', self.metadata_gb )
        self.refreshRate_s  = helperFunctions_UI.makeSpinBox( self.metadata_gb, 1, 120, 0, 1)
        self.refreshRate_s.setValue(self.plot_refreshRate)
        self.refreshRate_s.valueChanged.connect(self.initializeGraphing)
        self.displayTime_l  = helperFunctions_UI.makeLabel('Display Time (s)', self.metadata_gb )
        self.displayTime_t  = helperFunctions_UI.makeTextBox(self.metadata_gb )
        self.displayTime_t.setText('2')
        self.displayTime_t.textChanged.connect(self.initializeGraphing)
        self.pause_b        = helperFunctions_UI.makeButton('Pause', self.metadata_gb)
        self.pause_b.clicked.connect(self.click_pause)
        self.rescale_b      = helperFunctions_UI.makeButton('Rescale Plots', self.metadata_gb)
        self.rescale_b.clicked.connect(self.click_rescale)
        self.linkAxes_cb    = helperFunctions_UI.makeCheckBox('Link Axes', self.metadata_gb)
        self.linkAxes_cb.stateChanged.connect(  self.check_linkAxes)
        self.pathSave_l     = helperFunctions_UI.makeLabel('Save To:', self.metadata_gb )
        self.pathSave_t     = helperFunctions_UI.makeTextBox(self.metadata_gb )
        self.pathSave_b     = helperFunctions_UI.makeButton('Browse', self.metadata_gb )
        self.pathSave_t.setText(self.pathSave_default)
        self.pathSave_b.clicked.connect(self.click_pathSave)
        self.record_b       = helperFunctions_UI.makeButton('Record', self.metadata_gb )
        self.record_b.clicked.connect(self.click_record)
        width = 150
        self.bleDevice_t.setFixedWidth(width)
        # self.displayTime_l.setFixedWidth(width)
        # self.pause_b.setFixedWidth(width*2)
        # self.rescale_b.setFixedWidth(width*2)
        # self.linkAxes_cb.setFixedWidth(width*2)
        # self.labelNumber_sb.setFixedWidth(width)
        # self.displayTime_t.setFixedWidth(width*2)
        # self.pathSave_l.setFixedWidth(width)
        # self.pathSave_b.setFixedWidth(width)

        self.experimentLayout = helperFunctions_UI.makeHorizontalLayout([self.bleDevice_l,
                                                                         self.bleDevice_t,
                                                                         self.connect_b,
                                                                        #  self.voltageRail_dd,
                                                                        #  self.sampleRate_l,
                                                                        #  self.sampleRate_t,
                                                                         self.refreshRate_l,
                                                                         self.refreshRate_s,
                                                                         self.displayTime_l,
                                                                         self.displayTime_t, 
                                                                         self.pause_b, 
                                                                         self.rescale_b, 
                                                                         self.linkAxes_cb, 
                                                                         self.pathSave_l, 
                                                                         self.pathSave_t, 
                                                                         self.pathSave_b,
                                                                         self.record_b])

        self.mainLayout = helperFunctions_UI.makeVerticalLayout([ self.experimentLayout, self.channelLayout])

        self.setLayout(self.mainLayout)

        self.displayData = None
        self.displayIndicies  = None
        self.plotX_data = None
        self.filterCoef = None
        self.calculateAbs = None
        self.calculateZNormalize = None
        self.movingMeanWindow   = None
        self.movingMedianWindow = None
        self.movingRMSWindow    = None
        self.movingSumWindow    = None
        self.calculatePSD = None
        self.detectPeaks  = None
        self.peaksKwargs  = None

        self.thread    = None
        self.plotTimer = QtCore.QTimer()
        self.plotTimer.timeout.connect(self.updatePlot)
        self.initializeGraphing()


    def initializeGraphing(self):
        self.stopStream = True
        if self.recording:
            self.click_record()
        # Formally stop plotting
        self.plotTimer.stop()

        # self.fs               = int(self.sampleRate_t.toPlainText())
        self.plot_refreshRate = self.refreshRate_s.value()
        self.displayTime      = float(self.displayTime_t.toPlainText())
        self.bleDevice         = self.bleDevice_t.toPlainText()

        self.displayData = -2 * np.ones(int(self.num_channels*self.displayTime*self.fs))
        self.displayIndicies  = np.arange(0, int(self.displayTime * self.fs * self.num_channels))
        self.plotX_data = np.linspace(-1*self.displayTime, 0, num=int(self.displayTime*self.fs)).astype(float)
        self.filterCoef = [None] * self.num_channels
        self.calculateAbs = [False] * self.num_channels
        self.calculateZNormalize = [False] * self.num_channels
        self.movingMeanWindow   = [0] * self.num_channels
        self.movingMedianWindow = [0] * self.num_channels
        self.movingRMSWindow    = [0] * self.num_channels
        self.movingSumWindow    = [0] * self.num_channels
        self.calculatePSD = [False] * self.num_channels
        self.detectPeaks  = [False] * self.num_channels
        self.peaksKwargs  = [{}] * self.num_channels

        
        self.calculateFilterCoef()
        self.updateAbs()
        self.updateZNormalize()
        self.calculateMovingMeanWindow()
        self.calculateMovingMedianWindow()
        self.calculateMovingRMSWindow()
        self.calculateMovingSumWindow()
        self.updateFreq()

        self.plotTimer.start(int(1/self.plot_refreshRate))
        self.stopStream = False


    def stream(self):
        self.stopStream = False
        self.thread = threading.Thread(target=self.threadTarget)
        self.thread.daemon = True
        self.thread.start()
        self.plotTimer.start(int(1/self.plot_refreshRate))


    def threadTarget(self):
        self.connect_b.setEnabled(False)
        try:
            # asyncio.run handles loop creation/setting/closing for you.
            asyncio.run(self.bleConnect())
        except Exception as exc:
            print("Worker thread exception:", exc)
        finally:
            self.connect_b.setEnabled(True)
    

    async def bleConnect(self):
        device_search = self.bleDevice_t.toPlainText()
        device = await BleakScanner.find_device_by_name(device_search, timeout=5)
        if device is None:
            print(f"Device \"{device_search}\" not found.")
            self.connect_b.setEnabled(True)
            return
        
        while True:
            try:
                print(f"Attempting to connect to {device.name} @ {device.address} ...")
                async with BleakClient(device.address) as client:
                    print("Connected." if client.is_connected else "Failed to connect.")

                    # optional: check service/characteristic presence
                    if self.bleServiceUUID not in [s.uuid for s in client.services]:
                        print(f"Warning: Service {self.bleServiceUUID} not found on device.\nYou may have connected to the wrong device")
                    # start notify
                    await client.start_notify(self.bleCharUUID, self.unpackData)
                    print(f"Subscribed to notifications on {self.bleCharUUID}. Press Ctrl+C to stop.")

                    # wait until disconnected or interruption
                    while client.is_connected and not(self.stopStream):
                        await asyncio.sleep(1.0)

                    print("Disconnected from device.")
            except (BleakError, OSError) as e:
                print(f"Connection error: {e!r}")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"Unexpected error: {e!r}")

            if not self.stopStream:
                print(f"Reconnecting in {self.reconnectDelay} seconds...")
                await asyncio.sleep(self.reconnectDelay)



    quant = None
    signal_length = None
    sparse_rep = None
    chunk_active = False
    book_keeping = None

    def unpackData(self, sender, data):
        global quant, signal_length, sparse_rep, chunk_active, book_keeping
        packet_type = data[0]
        # the quant, signal length MUST be a float, int respectively
        if packet_type == 0x01:
            quant, num_levels = struct.unpack('<fb', data[1:6])
            book_keeping = struct.unpack('<' + 'i' * num_levels, data[6:6 + 4 * num_levels])
            signal_length = sum(book_keeping)
            sparse_rep = np.zeros(signal_length)
            chunk_active = True
            print(f"Received header: quant={quant}, signal_length={signal_length}, book_keeping={book_keeping}")
            return
        
        # packet id HAS to be an int, flags MUST be a byte
        if packet_type == 0x02 and chunk_active:
            packet_id, flags = struct.unpack('<BB', data[1:3])
            payload = data[3:]
            entry_size = 4 # uint16, int16 BEWARE one is signed!!!
            num_entries = len(payload) // entry_size

            print(f"packet_id={packet_id}, flags={flags}, num_entries={num_entries}")


            if flags & 0x01:  # it's a start of a new frame
                sparse_rep = np.zeros(signal_length)    
                print("Start of compressed chunk")
            
            
            for i in range(num_entries):
                entry = payload[i*entry_size:(i+1)*entry_size]
                idx, codeword = struct.unpack('<Hh', entry)
                if 0 <= idx < signal_length:
                    sparse_rep[idx] = codeword * quant

            if flags & 0x02:  # it's the end of the frame
                print("End of compressed chunk")
                start = 0
                coefficients = []
                for size in book_keeping:
                    coefficients.append(np.array(sparse_rep[start:start+size]))
                    start += size

                result = waverec(coefficients, 'db4', mode = 'symmetric')

                self.dataToDisplay.append(result)
                # write results to a csv file
                with open('decompressed_data_%s.csv' % len(result), 'a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(result)
                chunk_active = False

            else:
                if packet_type == 0x02:
                    print("Warning: Data packet arrived before start packet; skipping.")
                    print(f"packet_id={packet_id}, flags={flags}, num_entries={num_entries}")
            return



       
        

    def updatePlot(self):
        if len(self.dataToDisplay) == 0:
            return
        
        newData = self.dataToDisplay
        self.dataToDisplay = []
        newData = np.concatenate(newData,axis=-1).flatten(order='F').astype(float)

        if self.recording:
            self.fileRecording.write(newData.tobytes())

        # Necessary for autoscaling
        if len(self.plotX_data) != int(self.displayTime * self.fs) or (len(self.plotX_data) * self.num_channels) != len(self.displayIndicies):
            # Updates display indicies
            self.displayIndicies  = np.arange(0, int(self.displayTime * self.fs * self.num_channels))
            # Sets up the x axis for the data based on display time
            self.plotX_data = np.linspace(-1*self.displayTime, 0, num=int(self.displayTime * self.fs)).astype(float)

        # Shows if new data overflows
        if newData.shape[-1] > (self.displayTime*self.fs*self.num_channels):
            print('overflow!')
            newData = newData[-1*int(self.displayTime*self.fs*self.num_channels):]
        
        # Calculates the index where new data starts
        newDataSize = newData.shape[-1]
        newDataIndex = np.arange( self.displayIndex, self.displayIndex + newDataSize)
        # Puts new data into the new data indices
        np.put( self.displayData,  newDataIndex, newData,  mode='wrap')
        # Updates display index
        self.displayIndex += newDataSize
        # Sets up current display indices
        displayIndiciesCurrent = np.add( self.displayIndicies, self.displayIndex)
        # Gets the y axis for the data
        displayChannel  = np.take( self.displayData,  displayIndiciesCurrent, mode='wrap').astype(np.float64)

        if self.recording:
            self.plotX_data = np.add(self.plotX_data, newDataSize/(self.fs*self.num_channels))

        # print('\nmax: ', max(displayChannel), max(displayChannel) * self.convertToInt)
        # print('min: ', min(displayChannel), min(displayChannel) * self.convertToInt)
        if not self.displayPaused:
            for i in range(self.num_channels):
                d = displayChannel[i::self.num_channels]
                
                if self.filterCoef[i] is not None:
                    m = np.mean(d)
                    d = filtfilt( self.filterCoef[i][0], self.filterCoef[i][1], d-m) + m
                    
                if self.calculateAbs[i]:
                    d = np.abs(d)
                if self.calculateZNormalize[i]:
                    d = (d - np.mean(d)) / np.std(d)
                if self.movingMeanWindow[i] > 0:
                    d = move_mean( d, self.movingMeanWindow[i], min_count=1)
                if self.movingMedianWindow[i] > 0:
                    d = move_median( d, self.movingMedianWindow[i], min_count=1)
                if self.movingRMSWindow[i] > 0:
                    d = np.sqrt( move_mean( np.square(d), self.movingRMSWindow[i], min_count=1))
                if self.movingSumWindow[i] > 0:
                    d = move_sum( d, self.movingSumWindow[i], min_count=1)
                if self.calculatePSD[i]:
                    d_freq = self.coefficientPSD * np.square( np.abs( fft(d - np.mean(d))[:d.shape[-1]//2]))
                    d_freq[0] = d_freq[1:].min()
                    self.plots[i][1].setData(y=d_freq, x=self.plotX_freq)
                
                self.plots[i][0].setData(y=d, x=self.plotX_data)


    def calculateFilterCoef(self):
        nyq = self.fs * 0.5
        for i in range(self.num_channels):
            low  = self.filterL_t[i].toPlainText().strip()
            high = self.filterH_t[i].toPlainText().strip()
            order = self.filterOrder_s[i].value()
            try:
                if len(low) > 0:
                    if len(high) > 0:
                        self.filterCoef[i] = butter( order, [float(low)/nyq,float(high)/nyq], btype='bandpass', analog=False, output='ba')
                    else:
                        self.filterCoef[i] = butter( order, float(low)/nyq, btype='high', analog=False, output='ba')
                elif len(high) > 0:
                    self.filterCoef[i] = butter( order, float(high)/nyq, btype='low', analog=False, output='ba')
                else:
                    self.filterCoef[i] = None
            except:
                print('ERROR: Unable to calculate coefficients for "', low, '" and "', high, '"')
                self.filterCoef[i] = None


    def updateAbs(self):
        for i in range(self.num_channels):
            self.calculateAbs[i] = self.abs_cb[i].isChecked()
    

    def updateZNormalize(self):
        for i in range(self.num_channels):
            self.calculateZNormalize[i] = self.zNormalize_cb[i].isChecked()
    

    def calculateMovingMeanWindow(self):
        for i in range(self.num_channels):
            if self.movingMean_cb[i].isChecked():
                self.movingMean_t[i].setVisible(True)
                try:
                    self.movingMeanWindow[i] = int((float(self.movingMean_t[i].toPlainText()) / 1e3) * self.fs)
                except:
                    print('ERROR: Unable to calculate window size for "', self.movingMean_t[i].toPlainText(), '"')
                    self.movingMeanWindow[i] = 0
            else:
                self.movingMean_t[i].setVisible(False)
                self.movingMeanWindow[i] = 0


    def calculateMovingMedianWindow(self):
        for i in range(self.num_channels):
            if self.movingMedian_cb[i].isChecked():
                self.movingMedian_t[i].setVisible(True)
                try:
                    self.movingMedianWindow[i] = int((float(self.movingMedian_t[i].toPlainText()) / 1e3) * self.fs)
                except:
                    print('ERROR: Unable to calculate window size for "', self.movingMedian_t[i].toPlainText(), '"')
                    self.movingMedianWindow[i] = 0
            else:
                self.movingMedian_t[i].setVisible(False)
                self.movingMedianWindow[i] = 0


    def calculateMovingRMSWindow(self):
        for i in range(self.num_channels):
            if self.movingRMS_cb[i].isChecked():
                self.movingRMS_t[i].setVisible(True)
                try:
                    self.movingRMSWindow[i] = int((float(self.movingRMS_t[i].toPlainText()) / 1e3) * self.fs)
                except:
                    print('ERROR: Unable to calculate window size for "', self.movingRMS_t[i].toPlainText(), '"')
                    self.movingRMSWindow[i] = 0
            else:
                self.movingRMS_t[i].setVisible(False)
                self.movingRMSWindow[i] = 0


    def calculateMovingSumWindow(self):
        for i in range(self.num_channels):
            if self.movingSum_cb[i].isChecked():
                self.movingSum_t[i].setVisible(True)
                try:
                    self.movingSumWindow[i] = int((float(self.movingSum_t[i].toPlainText()) / 1e3) * self.fs)
                except:
                    print('ERROR: Unable to calculate window size for "', self.movingSum_t[i].toPlainText(), '"')
                    self.movingSumWindow[i] = 0
            else:
                self.movingSum_t[i].setVisible(False)
                self.movingSumWindow[i] = 0
    

    def updateFreq(self):
        self.plotX_freq = fftfreq(self.plotX_data.shape[-1], d=1/self.fs)[:self.plotX_data.shape[-1]//2]
        self.coefficientPSD = 2/(self.fs*self.plotX_data.shape[-1])
        for i in range(self.num_channels):
            if self.psd_cb[i].isChecked():
                self.graphicsViews[i][1].setVisible(True)
                self.plotItems[i][1].setXRange(0,5e3)
                self.calculatePSD[i] = True
            else:
                self.graphicsViews[i][1].setVisible(False)
                self.calculatePSD[i] = False


    def click_pathSave( self):
        folderName = QtWidgets.QFileDialog.getExistingDirectory( self, 'Select a Folder', )
        self.pathSave_t.setText(folderName)

    def click_rescale( self):
        for g in self.graphicsViews:
            for h in g:
                h.enableAutoRange()

    def click_pause(self):
        if self.displayPaused:
            self.pause_b.setText('Pause')
            self.displayPaused = False
        else:
            self.pause_b.setText('Resume')
            self.displayPaused = True
    
    def click_record(self):
        if self.recording:
            self.recording = False
            self.plotX_data = np.linspace(-1*self.displayTime, 0, num=int(self.displayTime*self.fs)).astype(float)
            self.fileRecording.close()
            self.record_b.setText('Record')
            self.record_b.setStyleSheet("background-color: grey;")
        else:
            ts = datetime.datetime.now()
            filename = '{:04d}.{:02d}.{:02d}.{:02d}.{:02d}.{:02d}_nidaq.bin'.format(ts.year,ts.month,ts.day,ts.hour,ts.minute,ts.second)
            self.fileRecording = open( os.path.join( self.pathSave_t.toPlainText(), filename), 'wb')
            headerByteArray = bytearray([ 1, # Version Number
                                         (int(self.fs)>>16)&0xFF, 
                                         (int(self.fs)>>8)&0xFF, 
                                          int(self.fs)&0xFF, 
                                          self.num_channels, 
                                          ts.year>>8, 
                                          ts.year&0xFF, 
                                          ts.month, 
                                          ts.day, 
                                          ts.hour, 
                                          ts.minute, 
                                          ts.second, 
                                          (int(ts.microsecond)>>16)&0xFF, 
                                          (int(ts.microsecond)>>8)&0xFF, 
                                          int(ts.microsecond)&0xFF])
            self.fileRecording.write(headerByteArray)
            self.recording = True
            self.record_b.setText('Stop Recording')
            self.record_b.setStyleSheet("background-color: red;")

    def check_linkAxes( self):
        # Toggles whether the axis are linked
        if self.linkAxes_cb.isChecked():
            for p in self.plotItems:
                p[0].setXLink(self.plotItems[0][0])
        else:
            for p in self.plotItems:
                p[0].setXLink(p[0])

    def closeEvent(self, event):
        print('closing...')

        try:
            self.stopStream = True
            if self.recording:
                self.recording = False
                self.fileRecording.close()
            # Formally close the thread
            if self.thread is not None:
                self.thread.join(timeout=1)
        except Exception as e:
            print('errors on closing...')
            print(e)

        print('Successfully closed.')
        event.accept()



if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    ui = mainWidget()
    ui.show()
    
    sys.exit(app.exec()) # PyQt6
    sys.exit(app.exec_()) # PyQt5


