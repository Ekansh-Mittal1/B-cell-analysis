# B-cell-repertoire-analysis


# Setup
install the required dependencies
```
pip3 install PyQt6
pip3 install qdarkstyle
pip3 install tabulate
pip3 install biopython
pip3 install pandas
pip3 install matplotlib
```

install changeo from their site

run the following code to install R libraries
```
if (!require("BiocManager", quietly = TRUE))
    install.packages("BiocManager")

BiocManager::install("shazam")
```
repeat for any dependencies

Finally, you must give permissions for the executable files needed
go to ```B-cell-repertoire-analysis-main/geneGUI/bin/``` and run every executable there.
If it says it cannot be opened, give it permisison as described [here](https://support.apple.com/guide/mac-help/apple-cant-check-app-for-malicious-software-mchleab3a043/mac)

# Starting the GUI

run the main.py file

# Features

 - IGBLAST analysis
