*******************************
			READ ME
*******************************

To run this application on Windows, you must use Anaconda, otherwise it is incredibly difficult to install the necessary scipy library without it. Install Anaconda from this link https://www.continuum.io/downloads#windows to download the Python 2.7 version

After Anaconda is installed, open a *new* terminal and type the following in this order: 

conda install mkl-service
conda install scipy
conda create --name py27 python=2.7
activate py27
conda install numpy
conda install scikit-learn
conda install matplotlib

*** your terminal should now say something like "(py27) C:\Users\...."

Navigate to the project directory, then type:

cd PEAK-0.5a4dev_r2085 and PEAK-Rules-0.5a1.dev-r2713
python setup.py install
cd ..
python StockPredictionMain.py

