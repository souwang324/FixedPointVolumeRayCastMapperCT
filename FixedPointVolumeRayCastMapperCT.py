


#!/usr/bin/env python

# noinspection PyUnresolvedReferences
import vtk
import vtkmodules.vtkInteractionStyle
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonDataModel import vtkPiecewiseFunction
from vtkmodules.vtkImagingHybrid import vtkSampleFunction
from vtkmodules.vtkIOLegacy import vtkStructuredPointsReader
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonDataModel import vtkImageData
from vtkmodules.vtkIOImage import vtkDICOMImageReader
from vtkmodules.vtkFiltersGeometry import vtkImageDataGeometryFilter
from vtkmodules.vtkIOXML import vtkXMLImageDataReader
#from vtkmodules.vtkFiltersSources import vtkSphereSource
from vtkmodules.vtkCommonCore import vtkStringArray
from vtkmodules.vtkCommonDataModel import (
    vtkCylinder,
    vtkSphere
)
from vtkmodules.vtkImagingCore import (
  vtkImageCast,
  vtkImageShiftScale
)
from vtkmodules.vtkRenderingCore import (
    vtkColorTransferFunction,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkRenderer,
    vtkVolume,
    vtkVolumeProperty
)
from vtkmodules.vtkRenderingVolume import vtkFixedPointVolumeRayCastMapper
# noinspection PyUnresolvedReferences
from vtkmodules.vtkRenderingVolumeOpenGL2 import vtkOpenGLRayCastImageDisplayHelper


def PrintUsage():
  print("Usage: \n")
  print("  FixedPointVolumeRayCastMapperCT <options>\n")
  print("where options may include: \n")
  print("  -DICOM <directory>\n")
  print("  -VTI <filename>\n")
  print("  -MHA <filename>\n")
  print("  -DependentComponents\n")
  print("  -Clip\n")
  print("  -MIP <window> <level>\n")
  print("  -CompositeRamp <window> <level>\n")
  print("  -CompositeShadeRamp <window> <level>\n")
  print("  -CT_Skin\n")
  print("  -CT_Bone\n")
  print("  -CT_Muscle\n")
  print("  -FrameRate <rate>\n")
  print("  -DataReduction <factor>\n")
  print("You must use either the -DICOM option to specify the directory where\n")
  print("the data is located or the -VTI or -MHA option to specify the path of a .vti file.\n")
  print("By default, the program assumes that the file has independent components \n")
  print("use -DependentComponents to specify that the file has dependent components.\n")
  print("Use the -Clip option to display a cube widget for clipping the volume.\n")
  print("Use the -FrameRate option with a desired frame rate (in frames per second)\n")
  print("which will control the interactive rendering rate.\n")
  print("Use the -DataReduction option with a reduction factor (greater than zero and\n")
  print("less than one) to reduce the data before rendering.\n")
  print("Use one of the remaining options to specify the blend function\n")
  print("and transfer functions. The -MIP option utilizes a maximum intensity\n")
  print("projection method, while the others utilize compositing. The\n")
  print("-CompositeRamp option is unshaded compositing, while the other\n")
  print("compositing options employ shading.\n")
  print("Note: MIP, CompositeRamp, CompositeShadeRamp, CT_Skin, CT_Bone,\n")
  print("and CT_Muscle are appropriate for DICOM data. MIP, CompositeRamp,\n")
  print("and RGB_Composite are appropriate for RGB data.\n")
  print( "Example: FixedPointVolumeRayCastMapperCT -DICOM CTNeck -MIP 4096 1024 \n")

def get_program_parameters():
  import argparse
  description = 'Read a VTK image data file.'
  epilogue = ''''''
  parser = argparse.ArgumentParser(description=description, epilog=epilogue,
                                   formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument('filename', help='./CT')
  args = parser.parse_args()
  return args.filename

def main():
  # Parse the parameters
  dirname = get_program_parameters()
  opacityWindow = 4096
  opacityLevel = 2048
  blendType = 6
  clip = 0
  reductionFactor = 1
  frameRate = 10.0
  independentComponents = True
  # Create the renderer, render window and interactor
  colors = vtkNamedColors()
  renderer = vtkRenderer()
  renWin = vtkRenderWindow()
  renWin.AddRenderer(renderer)

  # Connect it all. Note that funny arithematic on the
  # SetDesiredUpdateRate - the vtkRenderWindow divides it
  # allocated time across all renderers, and the renderer
  # divides it time across all props. If clip is
  # true then there are two props
  iren = vtkRenderWindowInteractor()
  iren.SetRenderWindow(renWin)
  iren.SetDesiredUpdateRate(frameRate / (1 + clip))
  iren.GetInteractorStyle().SetDefaultRenderer(renderer)

  # Read the data
  input = vtkImageData()
  dicomReader = vtkDICOMImageReader()
  dicomReader.SetDirectoryName(dirname)
  dicomReader.Update()
  input = dicomReader.GetOutput()

  # Verify that we actually have a volume
  dim =  input.GetDimensions()
  if (dim[0] < 2 or  dim[1] < 2 or dim[2] < 2):
    print("Error loading data!\n")
    return 1


  resample = vtk.vtkImageResample()
  if (reductionFactor < 1.0):
    resample.SetInputConnection(dicomReader.GetOutputPort())
    resample.SetAxisMagnificationFactor(0, reductionFactor)
    resample.SetAxisMagnificationFactor(1, reductionFactor)
    resample.SetAxisMagnificationFactor(2, reductionFactor)


  # Create our volume and mapper
  volume = vtkVolume()
  mapper = vtkFixedPointVolumeRayCastMapper()

  if (reductionFactor < 1.0):
    mapper.SetInputConnection(resample.GetOutputPort())
  else:
    mapper.SetInputConnection(dicomReader.GetOutputPort())

  # Set the sample distance on the ray to be 1/2 the average spacing
  if (reductionFactor < 1.0):
    spacing = resample.GetOutput().GetSpacing()
  else:
    spacing = input.GetSpacing()

  #  mapper.SetSampleDistance( (spacing[0]+spacing[1]+spacing[2])/6.0 )
  #  mapper.SetMaximumImageSampleDistance(10.0)

  # Create our transfer function
  colorFun = vtkColorTransferFunction()
  opacityFun = vtkPiecewiseFunction()
  # Create the property and attach the transfer functions
  property = vtkVolumeProperty()
  property.SetIndependentComponents(independentComponents)
  property.SetColor(colorFun)
  property.SetScalarOpacity(opacityFun)
  property.SetInterpolationTypeToLinear()

  # connect up the volume to the property and the mapper
  volume.SetProperty(property)
  volume.SetMapper(mapper)

  # Depending on the blend type selected as a command line option,
  # adjust the transfer function
  if (blendType == 0):
    ## MIP
    ## Create an opacity ramp from the window and level values.
    ## Color is white. Blending is MIP.
    colorFun.AddRGBSegment(0.0, 1.0, 1.0, 1.0, 255.0, 1.0, 1.0, 1.0)
    opacityFun.AddSegment(opacityLevel - 0.5 * opacityWindow, 0.0,
                           opacityLevel + 0.5 * opacityWindow, 1.0)
    mapper.SetBlendModeToMaximumIntensity()
  elif (blendType == 1):
    # CompositeRamp
    # Create a ramp from the window and level values. Use compositing
    # without shading. Color is a ramp from black to white.

    colorFun.AddRGBSegment(opacityLevel - 0.5 * opacityWindow, 0.0, 0.0, 0.0,
                            opacityLevel + 0.5 * opacityWindow, 1.0, 1.0, 1.0)
    opacityFun.AddSegment(opacityLevel - 0.5 * opacityWindow, 0.0,
                           opacityLevel + 0.5 * opacityWindow, 1.0)
    mapper.SetBlendModeToComposite()
    property.ShadeOff()
  elif (blendType == 2):
    # CompositeShadeRamp
    # Create a ramp from the window and level values. Use compositing
    # with shading. Color is white.
    colorFun.AddRGBSegment(0.0, 1.0, 1.0, 1.0, 255.0, 1.0, 1.0, 1.0)
    opacityFun.AddSegment(opacityLevel - 0.5 * opacityWindow, 0.0,
                           opacityLevel + 0.5 * opacityWindow, 1.0)
    mapper.SetBlendModeToComposite()
    property.ShadeOn()
  elif (blendType == 3):
    # CT_Skin
    # Use compositing and functions set to highlight skin in CT data
    # Not for use on RGB data
    colorFun.AddRGBPoint(-3024, 0, 0, 0, 0.5, 0.0)
    colorFun.AddRGBPoint(-1000, .62, .36, .18, 0.5, 0.0)
    colorFun.AddRGBPoint(-500, .88, .60, .29, 0.33, 0.45)
    colorFun.AddRGBPoint(3071, .83, .66, 1, 0.5, 0.0)

    opacityFun.AddPoint(-3024, 0, 0.5, 0.0)
    opacityFun.AddPoint(-1000, 0, 0.5, 0.0)
    opacityFun.AddPoint(-500, 1.0, 0.33, 0.45)
    opacityFun.AddPoint(3071, 1.0, 0.5, 0.0)

    mapper.SetBlendModeToComposite()
    property.ShadeOn()
    property.SetAmbient(0.1)
    property.SetDiffuse(0.9)
    property.SetSpecular(0.2)
    property.SetSpecularPower(10.0)
    property.SetScalarOpacityUnitDistance(0.8919)
  elif (blendType == 4):
    # CT_Bone
    # Use compositing and functions set to highlight bone in CT data
    # Not for use on RGB data
    colorFun.AddRGBPoint(-3024, 0, 0, 0, 0.5, 0.0)
    colorFun.AddRGBPoint(-16, 0.73, 0.25, 0.30, 0.49, .61)
    colorFun.AddRGBPoint(641, .90, .82, .56, .5, 0.0)
    colorFun.AddRGBPoint(3071, 1, 1, 1, .5, 0.0)

    opacityFun.AddPoint(-3024, 0, 0.5, 0.0)
    opacityFun.AddPoint(-16, 0, .49, .61)
    opacityFun.AddPoint(641, .72, .5, 0.0)
    opacityFun.AddPoint(3071, .71, 0.5, 0.0)

    mapper.SetBlendModeToComposite()
    property.ShadeOn()
    property.SetAmbient(0.1)
    property.SetDiffuse(0.9)
    property.SetSpecular(0.2)
    property.SetSpecularPower(10.0)
    property.SetScalarOpacityUnitDistance(0.8919)
  elif (blendType == 5):
    # CT_Muscle
    # Use compositing and functions set to highlight muscle in CT data
    # Not for use on RGB data
    colorFun.AddRGBPoint(-3024, 0, 0, 0, 0.5, 0.0)
    colorFun.AddRGBPoint(-155, .55, .25, .15, 0.5, .92)
    colorFun.AddRGBPoint(217, .88, .60, .29, 0.33, 0.45)
    colorFun.AddRGBPoint(420, 1, .94, .95, 0.5, 0.0)
    colorFun.AddRGBPoint(3071, .83, .66, 1, 0.5, 0.0)

    opacityFun.AddPoint(-3024, 0, 0.5, 0.0)
    opacityFun.AddPoint(-155, 0, 0.5, 0.92)
    opacityFun.AddPoint(217, .68, 0.33, 0.45)
    opacityFun.AddPoint(420, .83, 0.5, 0.0)
    opacityFun.AddPoint(3071, .80, 0.5, 0.0)

    mapper.SetBlendModeToComposite()
    property.ShadeOn()
    property.SetAmbient(0.1)
    property.SetDiffuse(0.9)
    property.SetSpecular(0.2)
    property.SetSpecularPower(10.0)
    property.SetScalarOpacityUnitDistance(0.8919)

  elif (blendType == 6):
    # RGB_Composite
    # Use compositing and functions set to highlight red/green/blue regions
    # in RGB data. Not for use on single component data
    opacityFun.AddPoint(0, 0.0)
    opacityFun.AddPoint(5.0, 0.0)
    opacityFun.AddPoint(30.0, 0.05)
    opacityFun.AddPoint(31.0, 0.0)
    opacityFun.AddPoint(90.0, 0.0)
    opacityFun.AddPoint(100.0, 0.3)
    opacityFun.AddPoint(110.0, 0.0)
    opacityFun.AddPoint(190.0, 0.0)
    opacityFun.AddPoint(200.0, 0.4)
    opacityFun.AddPoint(210.0, 0.0)
    opacityFun.AddPoint(245.0, 0.0)
    opacityFun.AddPoint(255.0, 0.5)

    mapper.SetBlendModeToComposite()
    property.ShadeOff()
    property.SetScalarOpacityUnitDistance(1.0)
  else:
    print("Unknown blend type.")

  # Set the default window size
  renWin.SetSize(600, 600)
  renWin.SetWindowName("FixedPointVolumeRayCastMapperCT")
  renWin.Render()

  # Add the volume to the scene
  renderer.AddVolume(volume)

  renderer.ResetCamera()
  color = colors.GetColor3d("SlateGray")
  renderer.SetBackground(color)

  camera = renderer.GetActiveCamera()
  camera.SetPosition(56.8656, -297.084, 78.913)
  camera.SetFocalPoint(109.139, 120.604, 63.5486)
  camera.SetViewUp(-0.00782421, -0.0357807, -0.999329)
  camera.SetDistance(421.227)
  camera.SetClippingRange(146.564, 767.987)

  # interact with data
  renWin.Render()

  iren.Start()

if __name__ == '__main__':
    main()