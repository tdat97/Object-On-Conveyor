# Object-On-Conveyor

Machine Vision On Conveyor With Learning Mode.
No Deep Learning, Only Opencv.
One Shot Learning.

---

### Configuration
 - Camera : Basler ( a2A2600-64ucBAS )
 - Arduino : COMFILE TECHNOLOGY ( FA-DUINO-12RA )
 - Photo Sensor : Autonics ( BY500-TDT or BTS1M-TDTD-P )
 - USB TO RS232 Converter
 - LED light
 - Extra

---

### Install

```
git clone https://github.com/tdat97/Object-On-Conveyor
cd Object-On-Conveyor
pip install -r requirments.txt
```

---

### Run

```
python run.py
```

---

##### The first screen
![OOC2](https://user-images.githubusercontent.com/48349693/217760314-98488099-14c1-4c2f-9524-d4c7260c7e78.png)
there are three buttons.
- read-mode button
- snap-mode button
- train-mode button

train-mode : one-shot, one-object-registration


##### The Read-Mode screen
![OOC](https://user-images.githubusercontent.com/48349693/217760413-717d983a-8cee-48a7-a671-35f5a004b5d0.png)


##### The Train-Mode Example
![small_one_shot](https://user-images.githubusercontent.com/48349693/220032335-a3114b9a-4fef-40c5-bc2c-688f7d6316d3.gif)


---

##### Circuit Wiring
![OOC회로](https://user-images.githubusercontent.com/48349693/217761864-568f0860-7dad-4d62-a3df-1b19b96a0690.png)









